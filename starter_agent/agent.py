import controlflow
import controlflow.events
import controlflow.orchestration
import controlflow.tools
import langchain_openai
import os
import queue
import rosetta
import rosetta.auditor
import rosetta.langchain
import rosetta.provider

from utils import TaskFactory
from utils import build_interaction_tool

# The Rosetta catalog provider serves versioned tools and prompts.
# For a comprehensive list of what parameters can be set here, see the class documentation.
# Parameters can also be set with environment variables (e.g., bucket = $ROSETTA_BUCKET).
provider = rosetta.Provider(
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
auditor = rosetta.auditor.Auditor(llm_name="gpt-4o")
chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o", temperature=0)


def run_flow(thread_id: str, to_user_queue: queue.Queue, from_user_queue: queue.Queue):
    # We provide a LangChain specific decorator (rosetta.langchain.audit) to inject this auditor into ChatModels.
    starter_agent = controlflow.Agent(
        name="Started Agent",
        model=rosetta.langchain.audit(chat_model, session=thread_id, auditor=auditor),
    )

    # Below, we have a helper class that removes some of the boilerplate for using Rosetta + ControlFlow.
    task_factory = TaskFactory(
        provider=provider,
        auditor=auditor,
        session=thread_id,
        agent=starter_agent,
        tools=[build_interaction_tool(to_user_queue, from_user_queue, auditor, thread_id)],
    )

    while True:
        # Write your agent logic here (note that start_conversation doesn't exist).
        start_conversation = task_factory.build(prompt_name="start_conversation")
        start_conversation.run()
