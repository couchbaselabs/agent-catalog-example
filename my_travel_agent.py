import dotenv

# Load our OPENAI_API_KEY first...
dotenv.load_dotenv()

# ...and then continue with the rest of the code.
import threading
import fastapi
import uuid
import multiprocessing
import dataclasses

import my_travel_flow

agent_server = fastapi.FastAPI()
registry_lock = threading.Semaphore()
flow_registry = dict()


@dataclasses.dataclass
class FlowHandle:
    flow_process: multiprocessing.Process
    to_user_queue: multiprocessing.Queue
    from_user_queue: multiprocessing.Queue


@agent_server.post("/start")
async def start_conversation():
    thread_id = uuid.uuid4().hex
    to_user_queue = multiprocessing.Queue(maxsize=1)
    from_user_queue = multiprocessing.Queue(maxsize=1)

    # Execute our flow (as a separate process)...
    flow_args = {'thread_id': thread_id, 'to_user_queue': to_user_queue, 'from_user_queue': from_user_queue}
    flow_process = multiprocessing.Process(
        target=my_travel_flow.run_flow,
        kwargs=flow_args
    )
    flow_process.start()

    # ...register our flow...
    try:
        registry_lock.acquire()
        flow_registry[thread_id] = FlowHandle(
            flow_process=flow_process,
            to_user_queue=to_user_queue,
            from_user_queue=from_user_queue,
        )
    finally:
        registry_lock.release()

    # ...and wait for the initial response to come back to our executor.
    initial_message = to_user_queue.get()
    return {
        'thread_id': thread_id,
        'initial_message': initial_message
    }


@agent_server.post("/chat/{thread_id}")
async def chat(thread_id: str, inp: str):
    try:
        registry_lock.acquire()
        flow_handle = flow_registry[thread_id]
        to_user_queue = flow_handle.to_user_queue
        from_user_queue = flow_handle.from_user_queue

    finally:
        registry_lock.release()

    # Place the input message in the 'from_user_queue'...
    from_user_queue.put(inp)

    # ...and wait for the output message to return.
    response = to_user_queue.get()
    return response
