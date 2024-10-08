import asyncio
import base64
import dotenv
import http
import json
import os
import pathlib
import requests
import requests.adapters
import streamlit
import streamlit_feedback
import threading
import time
import typing
import websockets.client

dotenv.load_dotenv()


@streamlit.cache_resource(show_spinner=True)
def create_loop():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return loop, thread


@streamlit.cache_resource(show_spinner=True)
def create_websocket():
    async def _connect():
        uri = f"ws://{os.getenv('AGENT_CONN_DOMAIN')}:{os.getenv('AGENT_CONN_PORT')}/chat"
        return await websockets.connect(uri)

    backoff_factor, retry_count = 1.0, 0
    while True:
        retry_count += 1
        try:
            return asyncio.run_coroutine_threadsafe(_connect(), streamlit.session_state.event_loop).result()
        except OSError:
            time.sleep(backoff_factor * (2 ** (retry_count - 1)))


# Define our title and sidebar.
streamlit.title("Your Agency's Travel Agent")
streamlit.divider()
with streamlit.sidebar:
    if "logo" not in streamlit.session_state:
        logo_path = pathlib.Path(__file__).parent / "resources" / "images" / "couchbase-logo.svg"
        with logo_path.open("r") as fp:
            streamlit.session_state.logo = fp.read()
    b64 = base64.b64encode(streamlit.session_state.logo.encode("utf-8")).decode("utf-8")
    streamlit.write(r'<img src="data:image/svg+xml;base64,%s"/>' % b64, unsafe_allow_html=True)
    streamlit.divider()
    streamlit.markdown(
        "This travel agent is powered by Couchbase Agent Catalog. See "
        "[here](https://github.com/couchbaselabs/rosetta-example) for more details!"
    )


# Our feedback is out-of-band, so we need to send it separately.
def feedback_callback_factory(assistant_message: str):
    def feedback_callback(feedback: typing.Dict):
        feedback_text = json.dumps(feedback)
        f_response = requests.post(
            streamlit.session_state.feedback_url,
            params={
                "content": "User has given the feedback " + feedback_text + " for the message: " + assistant_message
            },
        )
        assert f_response.status_code == http.HTTPStatus.OK
        streamlit.toast("Feedback received. Thank you!")

    return feedback_callback


# We need to gather messages until the agent is done thinking.
def gather_messages():
    while True:
        _message = asyncio.run_coroutine_threadsafe(
            streamlit.session_state.websocket.recv(), streamlit.session_state.event_loop
        ).result()
        _message = json.loads(_message)
        if not any(_message["content"] == m for m in streamlit.session_state.messages):
            streamlit.session_state.messages.append(_message)
            streamlit.caption(_message["content"])
        if _message["role"] == "assistant":
            break


# Establish our websocket connection.
if "is_connected" not in streamlit.session_state:
    streamlit.chat_input("Chat with the agent!", disabled=True)
    with streamlit.chat_message("assistant"), streamlit.status("Connecting to agent..."):
        streamlit.session_state.event_loop, worker_thread = create_loop()
        streamlit.session_state.websocket = create_websocket()
        streamlit.write("Websocket connection established.")
        thread_message = asyncio.run_coroutine_threadsafe(
            streamlit.session_state.websocket.recv(), streamlit.session_state.event_loop
        ).result()
        thread_id = json.loads(thread_message)["thread_id"]
        streamlit.session_state.thread_id = thread_id
        streamlit.session_state.feedback_url = (
            f"http://{os.getenv('AGENT_CONN_DOMAIN')}:{os.getenv('AGENT_CONN_PORT')}/feedback/"
            f"{streamlit.session_state.thread_id}"
        )
        streamlit.write("Connected to agent!")
        streamlit.session_state.is_connected = True
    streamlit.rerun()

elif "is_ready" not in streamlit.session_state:
    # We need to wait for our first assistant message to arrive to be "ready".
    streamlit.chat_input("Chat with the agent!", disabled=True)
    if "messages" not in streamlit.session_state:
        streamlit.session_state.messages = list()
    with streamlit.chat_message("assistant"), streamlit.status("(click here to see my thoughts)"):
        gather_messages()
    if any(message["role"] == "assistant" for message in streamlit.session_state.messages):
        streamlit.session_state.is_ready = True
        streamlit.rerun()

else:
    # Now we can chat! Load our old messages.
    websocket = streamlit.session_state.websocket
    message_iterator = iter(enumerate(streamlit.session_state.messages))
    try:
        i, message = next(message_iterator)
        while True:
            if message["role"] == "human":
                with streamlit.chat_message("human"):
                    streamlit.markdown(message["content"])
                i, message = next(message_iterator)
            else:
                with streamlit.chat_message("assistant"):
                    with streamlit.status("(click here to see my thoughts!)"):
                        while message["role"] != "assistant":
                            streamlit.caption(message["content"])
                            i, message = next(message_iterator)
                    streamlit.markdown(message["content"])
                    streamlit_feedback.streamlit_feedback(
                        feedback_type="faces",
                        on_submit=feedback_callback_factory(message["content"]),
                        key=str(i),
                    )
                i, message = next(message_iterator)

    except StopIteration:
        pass

    # And update our messages when a user inputs something.
    if user_input := streamlit.chat_input("Chat with the agent!"):
        user_message = {"role": "human", "content": user_input}
        streamlit.session_state.messages.append(user_message)
        with streamlit.chat_message(user_message["role"]):
            streamlit.markdown(user_message["content"])
        asyncio.run_coroutine_threadsafe(
            websocket.send(json.dumps(user_message)), streamlit.session_state.event_loop
        ).result()
        with streamlit.chat_message("assistant"), streamlit.status("(click here to see my thoughts)"):
            gather_messages()
        streamlit.rerun()
