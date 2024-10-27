import agentc
import agentc.langchain
import asyncio
import controlflow
import controlflow.events
import controlflow.events.events
import controlflow.orchestration
import controlflow.tools
import dotenv
import fastapi
import langchain_openai
import os
import pydantic
import typing

# Load our OPENAI_API_KEY.
dotenv.load_dotenv()

# The Agent Catalog provider serves versioned tools and prompts.
# For a comprehensive list of what parameters can be set here, see the class documentation.
# Parameters can also be set with environment variables (e.g., bucket = $AGENT_CATALOG_BUCKET).
provider = agentc.Provider(
    # This 'decorator' parameter tells us how tools should be returned (in this case, as a ControlFlow tool).
    decorator=lambda t: controlflow.tools.Tool.from_function(t.func),
    # Below, we define parameters that are passed to tools at runtime.
    # The 'keys' of this dictionary map to the values in various tool definitions (e.g., blogs_from_interests.yaml).
    # The 'values' of this dictionary map to actual values required by the tool.
    # In this case, we get the Couchbase connection string, username, and password from environment variables.
    secrets={
        "CB_CONN_STRING": os.getenv("CB_CONN_STRING"),
        "CB_USERNAME": os.getenv("CB_USERNAME"),
        "CB_PASSWORD": os.getenv("CB_PASSWORD"),
    },
)


# Below, we extend the Task class to track the (task-graph) walk our agent performs.
# In frameworks like LangGraph, this process is more straightforward due to edge traversal being a "first-class"
# concept.
class Task(controlflow.Task):
    _accept_status: typing.Callable = None

    def __init__(self, node_name: str, session: str, auditor: agentc.Auditor, **kwargs):
        super(Task, self).__init__(name=node_name, **kwargs)
        self._accept_status = lambda status, direction: auditor.move(
            node_name=node_name, direction=direction, session=session, content={"status": status.value}
        )

    def set_status(self, status: controlflow.tasks.task.TaskStatus):
        if status in controlflow.tasks.task.INCOMPLETE_STATUSES:
            direction = "enter"
        elif status in controlflow.tasks.task.COMPLETE_STATUSES:
            direction = "exit"
        else:
            raise ValueError(f"Invalid status encountered: {status}")
        super(Task, self).set_status(status)
        self._accept_status(status, direction)


async def run_flow(thread_id: str, websocket: fastapi.WebSocket):
    # The Agent Catalog LLM auditor will bind all LLM messages to...
    # 1. a specific catalog snapshot (i.e., the version of the catalog when the agent was started), and
    # 2. a specific conversation thread / session (passed in via session=thread_id).
    # Note: similar to a Agent Catalog provider, the parameters of an auditor can be set with environment variables.
    auditor = agentc.Auditor(agent_name="Couchbase Travel Agent")

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
        auditor.accept(kind=agentc.auditor.Kind.Assistant, content=message, session=thread_id)
        await websocket.send_json({"role": "assistant", "content": message})
        if get_response:
            response = await websocket.receive_json()
            auditor.accept(kind=agentc.auditor.Kind.Human, content=response["content"], session=thread_id)
            return response
        return "Message sent to user."

    # We provide a LangChain specific decorator (agentc.langchain.audit) to inject this auditor into ChatModels.
    chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o", temperature=0)
    travel_agent = controlflow.Agent(
        name="Couchbase Travel Agent",
        model=agentc.langchain.audit(chat_model, session=thread_id, auditor=auditor),
        tools=[talk_to_user],
    )

    with controlflow.Flow():
        callback_handler = controlflow.orchestration.handler.CallbackHandler(event_handler)
        while True:
            # Request router: find out what the user wants to do.
            user_intent_prompt = provider.get_prompt_for(query="getting user intent")
            user_intent = await Task(
                node_name="get_user_intent",
                auditor=auditor,
                session=thread_id,
                objective=user_intent_prompt.prompt,
                tools=user_intent_prompt.tools,
                agents=[travel_agent],
                result_type=["travel rewards", "trip planning", "about agency questions", "not applicable"],
            ).run_async(handlers=[callback_handler])

            # Decide the next task.
            match user_intent:
                case "travel rewards":
                    next_prompt = provider.get_prompt_for(query="managing rewards")
                    next_task = Task(
                        node_name="manage_rewards",
                        auditor=auditor,
                        session=thread_id,
                        objective=next_prompt.prompt,
                        tools=next_prompt.tools,
                        agents=[travel_agent],
                    )
                case "trip planning":
                    next_task = await _build_recommender_task(
                        thread_id=thread_id,
                        auditor=auditor,
                        travel_agent=travel_agent,
                        callback_handler=callback_handler,
                        talk_to_user=talk_to_user,
                    )
                case "about agency questions":
                    next_prompt = provider.get_prompt_for(query="answering questions")
                    next_task = Task(
                        node_name="answer_questions",
                        auditor=auditor,
                        session=thread_id,
                        objective=next_prompt.prompt,
                        tools=next_prompt.tools,
                        agents=[travel_agent],
                        result_type=str,
                    )
                case "not applicable":
                    next_prompt = provider.get_prompt_for(query="negative intent")
                    next_task = Task(
                        node_name="negative_intent",
                        auditor=auditor,
                        session=thread_id,
                        objective=next_prompt.prompt,
                        tools=next_prompt.tools,
                        agents=[travel_agent],
                    )
                case _:
                    raise RuntimeError("Bad response returned from agent!")
            await next_task.run_async(handlers=[callback_handler])
            if next_task.is_failed():
                failure_prompt = provider.get_prompt_for(query="handling failed task")
                await Task(
                    node_name="handle_failed_task",
                    auditor=auditor,
                    session=thread_id,
                    objective=failure_prompt.prompt,
                    tools=failure_prompt.tools,
                    agents=[travel_agent],
                ).run_async(handlers=[callback_handler])
                break

            # See if the user wants to continue.
            is_continue_prompt = provider.get_prompt_for(query="after addressing a user's request.")
            is_continue = await Task(
                node_name="ask_to_continue",
                auditor=auditor,
                session=thread_id,
                objective=is_continue_prompt.prompt,
                tools=is_continue_prompt.tools,
                agents=[travel_agent],
                result_type=[True, False],
            ).run_async(handlers=[callback_handler])
            if is_continue is False:
                break


async def _build_recommender_task(
    thread_id: str,
    auditor: agentc.Auditor,
    travel_agent: controlflow.Agent,
    callback_handler: controlflow.orchestration.Handler,
    talk_to_user: typing.Callable,
) -> controlflow.Task:
    # Task 1A: Decide on a destination by working with the user.
    recommend_destinations_prompt = provider.get_prompt_for(query="suggesting destination")
    recommended_destinations = await Task(
        node_name="suggest_destination",
        auditor=auditor,
        session=thread_id,
        objective=recommend_destinations_prompt.prompt,
        tools=recommend_destinations_prompt.tools,
        agents=[travel_agent],
        result_type=str,
    ).run_async(handlers=[callback_handler])

    # Task 1B: Find the closet airport to the user's destination.
    closet_dest_airport_prompt = provider.get_prompt_for(query="getting closest airport")
    closest_dest_airport = await Task(
        node_name="get_closest_airport",
        auditor=auditor,
        session=thread_id,
        objective=closet_dest_airport_prompt.prompt,
        tools=closet_dest_airport_prompt.tools,
        agents=[travel_agent],
        result_type=str,
        context={"location": recommended_destinations},
    ).run_async(handlers=[callback_handler])

    # Task 2A: Get the user's location.
    user_location_prompt = provider.get_prompt_for(query="getting user location")
    user_location = await Task(
        node_name="get_user_location",
        auditor=auditor,
        session=thread_id,
        objective=user_location_prompt.prompt,
        tools=user_location_prompt.tools,
        agents=[travel_agent],
        result_type=str,
    ).run_async(handlers=[callback_handler])

    # Task 2B: Find the closest airport to the user's location.
    closet_source_airport_prompt = provider.get_prompt_for(query="getting closest airport")
    closest_source_airport = await Task(
        node_name="get_closest_airport",
        auditor=auditor,
        session=thread_id,
        objective=closet_source_airport_prompt.prompt,
        tools=closet_source_airport_prompt.tools,
        agents=[travel_agent],
        result_type=str,
        context={"location": user_location},
    ).run_async(handlers=[callback_handler])

    # Tip: use Pydantic models to define the structure of the data you expect to receive!
    class TravelRoute(pydantic.BaseModel):
        airlines: typing.List[str]
        layovers: typing.List[str]
        from_airport: str
        to_airport: str

    # Part #3: find a route from the source airport to the destination airport.
    find_source_to_dest_route_prompt = provider.get_prompt_for(query="finding travel routes")
    source_to_dest_route = await Task(
        node_name="find_travel_routes",
        auditor=auditor,
        session=thread_id,
        objective=find_source_to_dest_route_prompt.prompt,
        tools=find_source_to_dest_route_prompt.tools,
        agents=[travel_agent],
        result_type=list[TravelRoute],
        context={"dest_airport": closest_dest_airport, "source_airport": closest_source_airport},
    ).run_async(handlers=[callback_handler])

    # Part #4: format the plan in Markdown.
    format_travel_plan_prompt = provider.get_prompt_for(query="formatting flight plan")
    formatted_travel_plan = await Task(
        node_name="format_flight_plan",
        auditor=auditor,
        session=thread_id,
        objective=format_travel_plan_prompt.prompt,
        tools=format_travel_plan_prompt.tools,
        agents=[travel_agent],
        result_type=str,
        context={
            "user_location": user_location,
            "travel_destination": recommended_destinations,
            "flight_plan": source_to_dest_route,
        },
    ).run_async(handlers=[callback_handler])

    # Part #5: return this plan back to the user.
    return_travel_plan_prompt = provider.get_prompt_for(query="returning flight plan")
    return Task(
        node_name="return_flight_plan",
        auditor=auditor,
        session=thread_id,
        objective=return_travel_plan_prompt.prompt,
        tools=return_travel_plan_prompt.tools,
        agents=[travel_agent],
        context={"travel_plan": formatted_travel_plan},
    )
