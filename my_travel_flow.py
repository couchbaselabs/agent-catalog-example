import controlflow
import controlflow.tools
import multiprocessing
import pydantic
import typing
import rosetta.core


def run_flow(thread_id: str, to_user_queue: multiprocessing.Queue, from_user_queue: multiprocessing.Queue):
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
        to_user_queue.put(message)
        if get_response:
            return from_user_queue.get()
        return "Message sent to user."

    provider_args = {'catalog_location': '.out/catalog.json'}
    travel_flow = controlflow.Flow(
        agents=[controlflow.Agent(name='Couchbase Travel Agent')],
        thread_id=thread_id
    )
    with rosetta.core.tools.LocalProvider(**provider_args) as tool_provider:
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
                    next_task = _build_rewards_task(tool_provider, talk_to_user)
                case 'trip planning':
                    next_task = _build_recommender_task(tool_provider, talk_to_user)
                case 'about agency questions':
                    next_task = _build_faq_answers_task(tool_provider, talk_to_user)
                case 'not applicable':
                    next_task = controlflow.Task(
                        objective='Tell the user that you cannot help them with their request and explain why.',
                        tools=[talk_to_user]
                    )
                case _:
                    raise RuntimeError('Bad response returned from agent!')
            travel_flow.add_task(next_task)
            travel_flow.run()

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


# TODO (GLENN): This part currently needs some TLC...
def _build_recommender_task(tool_provider: rosetta.core.tools.Provider, talk_to_user) -> controlflow.Task:
    with controlflow.Task(objective="Create a travel itinerary based on a user's interests.",
                          result_type=str) as build_travel_itinerary:
        # Part #1: get the travel destination airport.
        with controlflow.Task(objective="Get the user's destination airport.",
                              result_type=str) as get_travel_destination_airport:
            get_user_interests = controlflow.Task(
                objective="Get user's interests around travel.",
                tools=[talk_to_user],
                result_type=str
            )
            get_recommended_destinations = controlflow.Task(
                objective="Using the user interests, recommend travel destinations using travel blogs.",
                instructions="Ask the user to confirm a travel destination. Do not proceed unless the user says so!",
                result_type=str,
                tools=tool_provider.get_tools_for("reading travel blogs with user interests"),
                depends_on=[get_user_interests]
            )
            get_closest_dest_airport = controlflow.Task(
                objective="Locate the closet airport to the travel destination.",
                instructions="Using the travel destination, return the closet airport's IATA code.",
                result_type=str,
                depends_on=[get_recommended_destinations]
            )
            verify_dest_airport = controlflow.Task(
                objective="Make sure that the IATA code is valid.",
                tools=tool_provider.get_tools_for("checking airport codes"),
                depends_on=[get_closest_dest_airport]
            )

        # Part #2: get the user's location.
        with controlflow.Task(objective="Get the user's source airport.", result_type=str) as get_source_airport:
            get_user_location = controlflow.Task(
                objective="Ask the user for their location.",
                tools=[talk_to_user],
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
                tools=tool_provider.get_tools_for("checking airport codes"),
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
            instructions="Try to find a direct routes first between the source airport and the destination airport. "
                         "If there are no direct routes, then find a one-layover route. "
                         "If there are no such routes, then try another source airport that is close. ",
            result_type=list[TravelRoute],
            depends_on=[get_source_airport, get_travel_destination_airport],
            tools=tool_provider.get_tools_for('finding routes between airports')
        )

        format_travel_plan = controlflow.Task(
            objective="Format the flight plan into a document.",
            instructions="Use Markdown. Include the user location, travel destination, and flight plan.",
            result_type=str,
            depends_on=[find_source_to_dest_route]
        )
    return build_travel_itinerary


#
# Below, we define some dummy tasks.
#

def _build_rewards_task(_: rosetta.core.tools.Provider, talk_to_user) -> controlflow.Task:
    return controlflow.Task("Manage a user's travel rewards.", result_type=str)


def _build_faq_answers_task(_: rosetta.core.tools.Provider, talk_to_user) -> controlflow.Task:
    return controlflow.Task("Answer frequently asked questions above our travel agency.", result_type=str)
