import dotenv
import langchain_core.tools
import langchain_openai
import os
import pydantic
import queue
import rosetta
import rosetta.langchain
import typing

# Load our OPENAI_API_KEY first...
dotenv.load_dotenv()

# ...before loading control flow.
import controlflow
import controlflow.tools


def run_flow(thread_id: str, to_user_queue: queue.Queue, from_user_queue: queue.Queue):
    provider = rosetta.Provider(
        decorator=langchain_core.tools.StructuredTool.from_function,
        secrets={
            "CB_CONN_STRING": os.getenv("CB_CONN_STRING"),
            "CB_USERNAME": os.getenv("CB_USERNAME"),
            "CB_PASSWORD": os.getenv("CB_PASSWORD"),
        },
    )

    # Note: a limitation of ControlFlow is that this function MUST be called talk_to_user.
    def talk_to_user(message: str, get_response: bool = True) -> str:
        """
        Send a message to the human user and optionally wait for a response. If `get_response` is True, the function
        will return the user's response, otherwise it will return a simple confirmation. Do not send the user
        concurrent messages that require responses, as this will cause confusion.

        You may need to ask the human about multiple tasks at once. Consolidate your questions into a single message.
        For example, if Task 1 requires information X and Task 2 needs information Y, send a single message that
        naturally asks for both X and Y.
        """
        to_user_queue.join()
        to_user_queue.put(message)
        if get_response:
            response = from_user_queue.get()
            from_user_queue.task_done()
            return response
        return "Message sent to user."

    chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o")
    travel_agent = controlflow.Agent(
        name="Couchbase Travel Agent", model=rosetta.langchain.audit(chat_model=chat_model, session=thread_id)
    )
    with controlflow.Flow(agents=[travel_agent], thread_id=thread_id) as travel_flow:
        while True:
            # Request router: find out what the user wants to do.
            get_user_intent = controlflow.Task(
                objective="Ask the user what they need help with.",
                result_type=["travel rewards", "trip planning", "about agency questions", "not applicable"],
                tools=[talk_to_user],
            )
            travel_flow.add_task(get_user_intent)
            travel_flow.run()

            # Decide the next task.
            user_intent = get_user_intent.result
            match user_intent:
                case "travel rewards":
                    next_task = _build_rewards_task(provider, travel_flow, talk_to_user)
                case "trip planning":
                    next_task = _build_recommender_task(provider, travel_flow, talk_to_user)
                case "about agency questions":
                    next_task = _build_faq_answers_task(provider, travel_flow, talk_to_user)
                case "not applicable":
                    next_task = controlflow.Task(
                        objective="Tell the user that you cannot help them with their request and explain why.",
                        tools=[talk_to_user],
                    )
                case _:
                    raise RuntimeError("Bad response returned from agent!")
            travel_flow.run()
            if next_task.is_failed():
                controlflow.Task(
                    objective="Tell the user that you cannot help them with their request right now.",
                    tools=[talk_to_user],
                )
                travel_flow.run()
                break

            # See if the user wants to continue.
            ask_to_continue = controlflow.Task(
                objective="Ask the user if they want to continue.", result_type=[True, False], tools=[talk_to_user]
            )
            travel_flow.add_task(ask_to_continue)
            travel_flow.run()
            if ask_to_continue.result is False:
                break


def _build_recommender_task(
    provider: rosetta.Provider, parent_flow: controlflow.Flow, talk_to_user
) -> controlflow.Task:
    with parent_flow:
        # Task 1: Get the destination airport.
        get_user_interests = controlflow.Task(
            objective="Get user's interests around travel.", tools=[talk_to_user], result_type=str
        )
        get_recommended_destinations = controlflow.Task(
            objective="Using the user interests, find travel destinations using travel blogs.",
            result_type=str,
            context={"user_interests": get_user_interests},
            tools=provider.get_tools_for("reading travel blogs with user interests"),
            depends_on=[get_user_interests],
        )
        verify_recommended_destinations = controlflow.Task(
            objective="Ask the user to confirm a travel destination from the list of recommended destinations.",
            result_type=str,
            context={"destinations": get_recommended_destinations},
            depends_on=[get_recommended_destinations],
            tools=[talk_to_user],
        )
        get_closest_dest_airport = controlflow.Task(
            objective="Locate the closet airport to the travel destination.",
            instructions="Using the travel destination, return the closet airport's IATA code.",
            result_type=str,
            context={"destination": verify_recommended_destinations},
            depends_on=[verify_recommended_destinations],
        )
        verify_dest_airport = controlflow.Task(
            objective="Make sure that the IATA code is valid.",
            tools=provider.get_tools_for("checking airport codes"),
            context={"dest_airport": get_closest_dest_airport},
            depends_on=[get_closest_dest_airport],
        )

        # Part #2: get the source location.
        get_user_location = controlflow.Task(
            objective="Ask the user for their location.",
            tools=[talk_to_user],
            result_type=str,
        )
        get_closest_source_airport = controlflow.Task(
            objective="Locate the closet airport to the travel destination.",
            instructions="Using the user location, return th¡¡e closet airport's IATA code.",
            result_type=str,
            depends_on=[get_user_location],
        )
        verify_source_airport = controlflow.Task(
            objective="Make sure that the IATA code is valid.",
            tools=provider.get_tools_for("checking airport codes"),
            context={"source_airport": get_closest_source_airport},
            depends_on=[get_closest_source_airport],
        )

        class TravelRoute(pydantic.BaseModel):
            airlines: typing.List[str]
            layovers: typing.List[str]
            from_airport: str
            to_airport: str

        # Part #3: find a route from the source airport to the destination airport.
        find_source_to_dest_route = controlflow.Task(
            objective="Find a sequence of routes between the source airport and the destination airport.",
            instructions=provider.get_prompt_for("finding routes between airports"),
            result_type=list[TravelRoute],
            depends_on=[verify_source_airport, verify_dest_airport],
            context={"dest_airport": get_closest_dest_airport, "source_airport": get_closest_source_airport},
            tools=provider.get_tools_for("finding routes between airports", limit=2),
        )

        # Part #4: format the plan in Markdown.
        format_travel_plan = controlflow.Task(
            objective="Format the flight plan into a document.",
            instructions=("Use Markdown. Include the user location, travel destination, and flight plan. "),
            result_type=str,
            context={
                "user_location": get_user_location,
                "travel_destination": get_recommended_destinations,
                "flight_plan": find_source_to_dest_route,
            },
            depends_on=[find_source_to_dest_route],
        )

        # Part #5: return this plan back to the user.
        return_travel_plan = controlflow.Task(
            objective="Return the formatted travel plan back to the user. "
            "In the same message, ask if the travel plan looks okay to continue with."
            "DO NOT return a message without the travel plan.",
            result_type=None,
            depends_on=[format_travel_plan],
            context={"travel_plan": format_travel_plan},
            tools=[talk_to_user],
        )
        return return_travel_plan


def _build_rewards_task(provider: rosetta.Provider, parent_flow: controlflow.Flow, talk_to_user) -> controlflow.Task:
    with parent_flow:
        get_user_intent = controlflow.Task(
            objective="Help the user with their rewards.",
            tools=[talk_to_user] + provider.get_tools_for("travel rewards"),
        )
        return get_user_intent


def _build_faq_answers_task(
    provider: rosetta.Provider, parent_flow: controlflow.Flow, talk_to_user
) -> controlflow.Task:
    new_task = controlflow.Task("Answer frequently asked questions above our travel agency.", result_type=str)
    parent_flow.add_task(new_task)
    return new_task
