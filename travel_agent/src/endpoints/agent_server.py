import agentc
import fastapi
import logging
import uuid


# Choose which agent "version" to run! (preferably agent_c :-))
# from src.agent.agent_a import run_flow
from src.agent.agent_c import run_flow

agent_server = fastapi.FastAPI()
logger = logging.getLogger(__name__)


@agent_server.post("/feedback/{thread_id}")
def feedback(thread_id: str, content: str):
    auditor = agentc.Auditor(agent_name="Couchbase Travel Agent")
    auditor.accept(
        kind=agentc.auditor.Kind.Feedback,
        content=content,
        session=thread_id,
    )
    return fastapi.Response(status_code=200)


@agent_server.websocket("/chat")
async def chat(websocket: fastapi.WebSocket):
    await websocket.accept()
    logger.debug("Websocket connection established.")

    # First, give the user a unique thread id.
    thread_id = uuid.uuid4().hex
    await websocket.send_json({"thread_id": thread_id})
    logger.debug(f"Assigned thread id: {thread_id}")

    # Now we can start chatting!
    await run_flow(thread_id, websocket)
    await websocket.close()
    logger.debug("Websocket connection closed.")
