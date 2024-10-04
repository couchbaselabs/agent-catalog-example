import agent_catalog
import agent_catalog.auditor
import agent_catalog.langchain
import agent_catalog.provider
import controlflow
import controlflow.events
import controlflow.orchestration
import controlflow.tools
import dotenv
import langchain_openai
import os
import pydantic
import queue
import typing

try:
    from utils import TaskFactory
    from utils import build_interaction_tool
except ModuleNotFoundError:
    from .utils import TaskFactory
    from .utils import build_interaction_tool

# Load our OPENAI_API_KEY.
dotenv.load_dotenv()

# The Rosetta catalog provider serves versioned tools and prompts.
# For a comprehensive list of what parameters can be set here, see the class documentation.
# Parameters can also be set with environment variables (e.g., bucket = $ROSETTA_BUCKET).
provider = agent_catalog.Provider(
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

# The Rosetta LLM auditor will bind all LLM messages to...
# 1. a specific Rosetta catalog snapshot (i.e., the version of the catalog when the agent was started), and
# 2. a specific conversation thread / session (passed in via session=thread_id).
# Note: similar to a Rosetta provider, the parameters of a Rosetta auditor can be set with environment variables.
auditor = agent_catalog.auditor.Auditor(llm_name="gpt-4o")
chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o", temperature=0)


def run_flow(thread_id: str, to_user_queue: queue.Queue, from_user_queue: queue.Queue):
    # We provide a LangChain specific decorator (agent_catalog.langchain.audit) to inject this auditor into ChatModels.
    travel_agent = controlflow.Agent(
        name="Couchbase Travel Agent",
        model=agent_catalog.langchain.audit(chat_model, session=thread_id, auditor=auditor),
    )
    flow = controlflow.Flow(default_agent=travel_agent, thread_id=thread_id)

    # Below, we have a helper class that removes some of the boilerplate for using Rosetta + ControlFlow.
    task_factory = TaskFactory(
        provider=provider,
        auditor=auditor,
        session=thread_id,
        agent=travel_agent,
        tools=[build_interaction_tool(to_user_queue, from_user_queue, auditor, thread_id)],
    )
    while True:
        # Request router: find out what the user wants to do.
        get_user_intent = task_factory.build(
            prompt_name="get_user_intent",
            result_type=["travel rewards", "trip planning", "about agency questions", "not applicable"],
        )
        controlflow.run_tasks([get_user_intent], flow=flow)

        # Decide the next task.
        user_intent = get_user_intent.result
        match user_intent:
            case "travel rewards":
                next_task = task_factory.build(prompt_name="manage_rewards")
            case "trip planning":
                next_task = _build_recommender_task(task_factory)
            case "about agency questions":
                next_task = task_factory.build(prompt_name="answer_questions", result_type=str)
            case "not applicable":
                next_task = task_factory.build(prompt_name="negative_intent")
            case _:
                raise RuntimeError("Bad response returned from agent!")
        controlflow.run_tasks([next_task], flow=flow)
        if next_task.is_failed():
            controlflow.run_tasks([task_factory.build(prompt_name="handle_failed_task")], flow=flow)
            break

        # See if the user wants to continue.
        ask_to_continue = task_factory.build(
            prompt_name="ask_to_continue",
            result_type=[True, False],
        )
        controlflow.run_tasks([ask_to_continue], flow=flow)
        if ask_to_continue.result is False:
            break


def _build_recommender_task(task_factory: TaskFactory) -> controlflow.Task:
    # Task 1: Get the destination airport.
    get_recommended_destinations = task_factory.build(
        prompt_name="suggest_destination",
        result_type=str,
    )
    get_closest_dest_airport = task_factory.build(
        prompt_name="get_closest_airport",
        result_type=str,
        context={"location": get_recommended_destinations},
        depends_on=[get_recommended_destinations],
    )

    # Part #2: get the source location.
    get_user_location = task_factory.build(
        prompt_name="get_user_location",
        result_type=str,
    )
    get_closest_source_airport = task_factory.build(
        prompt_name="get_closest_airport",
        result_type=str,
        context={"location": get_user_location},
        depends_on=[get_user_location],
    )

    class TravelRoute(pydantic.BaseModel):
        airlines: typing.List[str]
        layovers: typing.List[str]
        from_airport: str
        to_airport: str

    # Part #3: find a route from the source airport to the destination airport.
    find_source_to_dest_route = task_factory.build(
        prompt_name="find_travel_routes",
        result_type=list[TravelRoute],
        depends_on=[get_closest_dest_airport, get_closest_source_airport],
        context={"dest_airport": get_closest_dest_airport, "source_airport": get_closest_source_airport},
    )

    # Part #4: format the plan in Markdown.
    format_travel_plan = task_factory.build(
        prompt_name="format_flight_plan",
        result_type=str,
        context={
            "user_location": get_user_location,
            "travel_destination": get_recommended_destinations,
            "flight_plan": find_source_to_dest_route,
        },
        depends_on=[find_source_to_dest_route],
    )

    # Part #5: return this plan back to the user.
    return_travel_plan = task_factory.build(
        prompt_name="return_flight_plan",
        result_type=None,
        depends_on=[format_travel_plan],
        context={"travel_plan": format_travel_plan},
    )
    return return_travel_plan
