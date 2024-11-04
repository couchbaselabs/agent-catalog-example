import asyncio
import controlflow.events.events
import dotenv
import fastapi
import langchain_openai

from ..resources.agent_a import tools

# Load our OPENAI_API_KEY.
dotenv.load_dotenv()


async def run_flow(thread_id: str, websocket: fastapi.WebSocket):
    # To show "thinking" in our app, we'll add an event handler here.
    def event_handler(event: controlflow.events.Event):
        if isinstance(event, controlflow.events.events.OrchestratorMessage):
            content = event.content
        elif isinstance(event, controlflow.events.events.ToolCallEvent):
            content = event.tool_call
        elif isinstance(event, controlflow.events.events.ToolResultEvent):
            content = {"tool_call": event.tool_call, "tool_result": event.tool_result.str_result}
        elif isinstance(event, controlflow.events.events.AgentMessage):
            content = event.message
        else:
            return
        asyncio.create_task(websocket.send_json({"role": "system", "content": content}))

    # In some agent frameworks like LangChain, user input is explicitly handled by the developer. In agent frameworks
    # like ControlFlow, user input is just another tool call.
    async def talk_to_user(message: str, get_response: bool = True) -> str:
        """
        Send a message to the human user and optionally wait for a response. If `get_response` is True, the function
        will return the user's response, otherwise it will return a simple confirmation. Do not send the user
        concurrent messages that require responses, as this will cause confusion.

        You may need to ask the human about multiple tasks at once. Consolidate your questions into a single message.
        For example, if Task 1 requires information X and Task 2 needs information Y, send a single message that
        naturally asks for both X and Y.
        """
        await websocket.send_json({"role": "assistant", "content": message})
        if get_response:
            response = await websocket.receive_json()
            return response
        return "Message sent to user."

    # ControlFlow agents (and many other agent frameworks) accept LangChain chat models as LLM interfaces.
    chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o", temperature=0)
    travel_agent = controlflow.Agent(
        name="Couchbase Travel Agent",
        model=chat_model,
        tools=[talk_to_user],
    )

    with controlflow.Flow():
        callback_handler = controlflow.orchestration.handler.CallbackHandler(event_handler)
        while True:
            # Request router: find out what the user wants to do.
            user_intent = await controlflow.Task(
                objective="""
                Ask the user what they need help with.
                NEVER assume the user intent, always ask them first.
                """,
                tools=[talk_to_user],
                agents=[travel_agent],
                result_type=["travel rewards", "trip planning", "about agency questions", "not applicable"],
            ).run_async(handlers=[callback_handler])

            # Decide the next task.
            match user_intent:
                case "travel rewards":
                    next_prompt = """
                    Help the user with their rewards.
                    Do not hallucinate, always use the tools you were given.
                    """
                    next_task = tools.controlflow.Task(
                        objective=next_prompt,
                        tools=[
                            tools.create_new_travel_rewards_member,
                            tools.get_travel_rewards_for_member,
                            talk_to_user,
                        ],
                        agents=[travel_agent],
                    )
                case "trip planning":
                    next_task = await _build_recommender_task(
                        travel_agent=travel_agent,
                        callback_handler=callback_handler,
                        talk_to_user=talk_to_user,
                    )
                case "about agency questions":
                    next_prompt = """
                    Answer frequently asked questions above our travel agency.
                    Hallucinate as much as you'd like, just make it sound real but keep a professional persona.
                    You MUST talk back to the user (use your talk_to_user tool and communicate your response to them).
                    """
                    next_task = controlflow.Task(
                        objective=next_prompt,
                        tools=[talk_to_user],
                        agents=[travel_agent],
                        result_type=str,
                    )
                case "not applicable":
                    next_prompt = """
                    Tell the user that you cannot help them with their request and explain why.
                    """
                    next_task = controlflow.Task(
                        objective=next_prompt,
                        tools=[talk_to_user],
                        agents=[travel_agent],
                    )
                case _:
                    raise RuntimeError("Bad response returned from agent!")
            await next_task.run_async(handlers=[callback_handler])
            if next_task.is_failed():
                failure_prompt = """
                Tell the user that you cannot help them with their request right now.
                You MUST talk to the user here and communicate your response to them.
                """
                await controlflow.Task(
                    objective=failure_prompt,
                    tools=[talk_to_user],
                    agents=[travel_agent],
                ).run_async(handlers=[callback_handler])
                break

            # See if the user wants to continue.
            is_continue_prompt = """
            Ask the user if they want to continue.
            If they say yes, then return true.
            If they say no, return false.
            When in doubt, ask the user again for clarification.
            """
            is_continue = await controlflow.Task(
                objective=is_continue_prompt,
                tools=[talk_to_user],
                agents=[travel_agent],
                result_type=[True, False],
            ).run_async(handlers=[callback_handler])
            if is_continue is False:
                break


async def _build_recommender_task(
    travel_agent: controlflow.Agent,
    callback_handler: controlflow.orchestration.Handler,
    talk_to_user: tools.typing.Callable,
) -> controlflow.Task:
    # Task 1A: Decide on a destination by working with the user.
    recommend_destinations_prompt = """
    Your objective is to follow the plan below.
    DO NOT deviate from the following plan.

    Plan:
    1. Get a user's interests around travel. Ask them about their hobbies.
    2. Using the user's interests, find travel destinations using travel blogs.
       DO NOT hallucinate travel destinations, you must use a tool to find travel blog snippets first.
    3. Ask the user to confirm their travel destination from the list of recommended destinations.
       You MUST ask the user to confirm their travel destination.
    """
    recommended_destinations = await controlflow.Task(
        objective=recommend_destinations_prompt,
        tools=[tools.get_travel_blog_snippets_from_user_interests, talk_to_user],
        agents=[travel_agent],
        result_type=str,
    ).run_async(handlers=[callback_handler])

    # Task 1B: Find the closet airport to the user's destination.
    closet_dest_airport_prompt = """
    Using the given location, return the closet airport's IATA code.
    You must use a tool to verify that the IATA code is valid.
    DO NOT continue until you can verify that the IATA code is valid.
    """
    closest_dest_airport = await controlflow.Task(
        objective=closet_dest_airport_prompt,
        tools=[tools.check_if_airport_exists],
        agents=[travel_agent],
        result_type=str,
        context={"location": recommended_destinations},
    ).run_async(handlers=[callback_handler])

    # Task 2A: Get the user's location.
    user_location_prompt = """
    Ask the user for their location.
    """
    user_location = await controlflow.Task(
        objective=user_location_prompt,
        tools=[talk_to_user],
        agents=[travel_agent],
        result_type=str,
    ).run_async(handlers=[callback_handler])

    # Task 2B: Find the closest airport to the user's location.
    closet_source_airport_prompt = closet_dest_airport_prompt
    closest_source_airport = await controlflow.Task(
        objective=closet_source_airport_prompt,
        tools=[tools.check_if_airport_exists],
        agents=[travel_agent],
        result_type=str,
        context={"location": user_location},
    ).run_async(handlers=[callback_handler])

    # Tip: use Pydantic models to define the structure of the data you expect to receive!
    class TravelRoute(tools.pydantic.BaseModel):
        airlines: tools.typing.List[str]
        layovers: tools.typing.List[str]
        from_airport: str
        to_airport: str

    # Part #3: find a route from the source airport to the destination airport.
    find_source_to_dest_route_prompt = """
    Find a sequence of routes between the source airport and the destination airport.

    Try to find a direct routes first between the source airport and the destination airport.
    If there are no direct routes, then find a one-layover route.
    If there are no such routes, then try another source airport that is close.
    """
    source_to_dest_route = await controlflow.Task(
        objective=find_source_to_dest_route_prompt,
        tools=[tools.find_direct_routes_between_airports, tools.find_routes_with_one_layover],
        agents=[travel_agent],
        result_type=list[TravelRoute],
        context={"dest_airport": closest_dest_airport, "source_airport": closest_source_airport},
    ).run_async(handlers=[callback_handler])

    # Part #4: format the plan in Markdown.
    format_travel_plan_prompt = """
    Objective:
    Format the flight plan into a document.
    Use Markdown. Include the user location, travel destination, and flight plan.

    Examples:
    # Your Travel Itinerary

    ## Flying from Hawaii
    Your travel will start in Hawaii, a beautiful island with ...

    ## Flying to San Francisco
    Your travel will end in San Francisco. We recommend the following places:

    ## Flight Plan
    1. Hawaii to Hilo
    2. Hilo to SFO
    """
    formatted_travel_plan = await controlflow.Task(
        objective=format_travel_plan_prompt,
        tools=[],
        agents=[travel_agent],
        result_type=str,
        context={
            "user_location": user_location,
            "travel_destination": recommended_destinations,
            "flight_plan": source_to_dest_route,
        },
    ).run_async(handlers=[callback_handler])

    # Part #5: return this plan back to the user.
    return_travel_plan_prompt = """
    Return the formatted travel plan back to the user.
    In the same message, ask if the travel plan looks okay to continue with.
    DO NOT return a message without the travel plan.
    """
    return controlflow.Task(
        objective=return_travel_plan_prompt,
        tools=[talk_to_user],
        agents=[travel_agent],
        context={"travel_plan": formatted_travel_plan},
    )
