import os
import rosetta.core
import pydantic
import dataclasses
import sentence_transformers
import typing
import queue
import dotenv

# Load our OPENAI_API_KEY first...
dotenv.load_dotenv()

# ...before loading control flow.
import controlflow
import controlflow.tools


@dataclasses.dataclass
class TaskBuilderContext:
    tool_provider: rosetta.core.tool.Provider
    parent_flow: controlflow.Flow
    talk_to_user: typing.Callable


def run_flow(thread_id: str, to_user_queue: queue.Queue, from_user_queue: queue.Queue):
    # TODO (GLENN): Finish the capabilities to load tools + prompts from a CB instance.
    embedding_model = sentence_transformers.SentenceTransformer(os.getenv('DEFAULT_SENTENCE_EMODEL'))
    # TODO: We should instead grab the embedding_model name from the catalog
    # as it remembers it in the meta.json.
    tool_provider = rosetta.core.tool.LocalProvider(
        catalog_file='.rosetta-catalog/tool_catalog.json',
        embedding_model=embedding_model
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

    # TODO (GLENN): Replace this with Kush's agent.
    travel_flow = controlflow.Flow(
        agents=[controlflow.Agent(name='Couchbase Travel Agent')],
        thread_id=thread_id
    )
    with tool_provider as tool_provider, \
            travel_flow as travel_flow:
        tbc = TaskBuilderContext(
            tool_provider=tool_provider,
            parent_flow=travel_flow,
            talk_to_user=talk_to_user
        )
        while True:
            # Request router: find out what the user wants to do.
            get_user_intent = controlflow.Task(
                objective="Ask the user what they need help with.",
                result_type=[
                    'travel rewards',
                    'trip planning',
                    'about agency questions',
                    'not applicable'
                ],
                tools=[talk_to_user]
            )
            travel_flow.add_task(get_user_intent)
            travel_flow.run()

            # Decide the next task.
            user_intent = get_user_intent.result
            match user_intent:
                case 'travel rewards':
                    next_task = _build_rewards_task(tbc)
                case 'trip planning':
                    next_task = _build_recommender_task(tbc)
                case 'about agency questions':
                    next_task = _build_faq_answers_task(tbc)
                case 'not applicable':
                    next_task = controlflow.Task(
                        objective='Tell the user that you cannot help them with their request and explain why.',
                        tools=[talk_to_user]
                    )
                case _:
                    raise RuntimeError('Bad response returned from agent!')
            travel_flow.run()
            if next_task.is_failed():
                controlflow.Task(
                    objective="Tell the user that you cannot help them with their request right now.",
                    tools=[talk_to_user]
                )
                travel_flow.run()
                break

            # See if the user wants to continue.
            ask_to_continue = controlflow.Task(
                objective="Ask the user if they want to continue.",
                result_type=[True, False],
                tools=[talk_to_user]
            )
            travel_flow.add_task(ask_to_continue)
            travel_flow.run()
            if ask_to_continue.result is False:
                break


def _build_recommender_task(tbc: TaskBuilderContext) -> controlflow.Task:
    with tbc.parent_flow:
        # Task 1: Get the destination airport.
        get_user_interests = controlflow.Task(
            objective="Get user's interests around travel.",
            tools=[tbc.talk_to_user],
            result_type=str
        )
        get_recommended_destinations = controlflow.Task(
            objective="Using the user interests, find travel destinations using travel blogs.",
            result_type=str,
            context={'user_interests': get_user_interests},
            tools=tbc.tool_provider.get_tools_for("reading travel blogs with user interests"),
            depends_on=[get_user_interests]
        )
        verify_recommended_destinations = controlflow.Task(
            objective="Ask the user to confirm a travel destination from the list of recommended destinations.",
            result_type=str,
            context={'destinations': get_recommended_destinations},
            depends_on=[get_recommended_destinations],
            tools=[tbc.talk_to_user]
        )
        get_closest_dest_airport = controlflow.Task(
            objective="Locate the closet airport to the travel destination.",
            instructions="Using the travel destination, return the closet airport's IATA code.",
            result_type=str,
            context={'destination': verify_recommended_destinations},
            depends_on=[verify_recommended_destinations]
        )
        verify_dest_airport = controlflow.Task(
            objective="Make sure that the IATA code is valid.",
            tools=tbc.tool_provider.get_tools_for("checking airport codes"),
            context={'dest_airport': get_closest_dest_airport},
            depends_on=[get_closest_dest_airport],
        )

        # Part #2: get the source location.
        get_user_location = controlflow.Task(
            objective="Ask the user for their location.",
            tools=[tbc.talk_to_user],
            result_type=str,
        )
        get_closest_source_airport = controlflow.Task(
            objective="Locate the closet airport to the travel destination.",
            instructions="Using the user location, return the closet airport's IATA code.",
            result_type=str,
            depends_on=[get_user_location]
        )
        verify_source_airport = controlflow.Task(
            objective="Make sure that the IATA code is valid.",
            tools=tbc.tool_provider.get_tools_for("checking airport codes"),
            context={'source_airport': get_closest_source_airport},
            depends_on=[get_closest_source_airport]
        )

        class TravelRoute(pydantic.BaseModel):
            airlines: typing.List[str]
            layovers: typing.List[str]
            from_airport: str
            to_airport: str

        # Part #3: find a route from the source airport to the destination airport.
        find_source_to_dest_route = controlflow.Task(
            objective="Find a sequence of routes between the source airport and the destination airport.",
            instructions=(
                "Try to find a direct routes first between the source airport and the destination airport. "
                "If there are no direct routes, then find a one-layover route. "
                "If there are no such routes, then try another source airport that is close. "
            ),
            result_type=list[TravelRoute],
            depends_on=[verify_source_airport, verify_dest_airport],
            context={'dest_airport': get_closest_dest_airport,
                     'source_airport': get_closest_source_airport},
            tools=tbc.tool_provider.get_tools_for('finding routes between airports', k=2)
        )

        # Part #4: format the plan in Markdown.
        format_travel_plan = controlflow.Task(
            objective="Format the flight plan into a document.",
            instructions=(
                "Use Markdown. Include the user location, travel destination, and flight plan. "
                "Return this formatted plan to the user. "
            ),
            result_type=str,
            tools=[tbc.talk_to_user],
            depends_on=[find_source_to_dest_route]
        )
        return format_travel_plan


#
# Below, we define some dummy tasks.
#

def _build_rewards_task(tbc: TaskBuilderContext) -> controlflow.Task:
    with tbc.parent_flow:
        get_user_intent = controlflow.Task(
            objective="Help the user with their rewards.",
            tools=[tbc.talk_to_user] + tbc.tool_provider.get_tools_for('travel rewards')
        )
        return get_user_intent


def _build_faq_answers_task(tbc: TaskBuilderContext) -> controlflow.Task:
    new_task = controlflow.Task("Answer frequently asked questions above our travel agency.", result_type=str)
    tbc.parent_flow.add_task(new_task)
    return new_task
