import dotenv
import http
import json
import os
import requests.adapters
import streamlit
import streamlit_feedback
import typing


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


# Our first-time actions: initialize a conversation with our agent.
if "thread_id" not in streamlit.session_state:
    dotenv.load_dotenv()

    # Determine our agent endpoints.
    agent_server_url = f"http://{os.getenv('AGENT_CONN_DOMAIN')}:{os.getenv('AGENT_CONN_PORT')}"
    start_url = agent_server_url + "/start"
    chat_url = agent_server_url + "/chat"
    feedback_url = agent_server_url + "/feedback"

    # Here, we make our initial call to our agent. We might need to retry.
    retries = requests.adapters.Retry(total=10, backoff_factor=0.1)
    session = requests.Session()
    session.mount("http://", requests.adapters.HTTPAdapter(max_retries=retries))
    response = session.post(start_url)
    if response.status_code != http.HTTPStatus.OK:
        raise EnvironmentError("Cannot connect to agent server!")
    response_json = response.json()
    session.close()

    # Save our thread_id and the initial messages.
    streamlit.session_state.thread_id = response_json["thread_id"]
    streamlit.session_state.chat_url = chat_url + "/" + response_json["thread_id"]
    streamlit.session_state.feedback_url = feedback_url + "/" + response_json["thread_id"]
    streamlit.session_state.messages = [{"role": "assistant", "content": response_json["initial_message"]}]

streamlit.title("Couchbase Travel Agent")

# On refresh, we should not lose any of our messages.
for i, message in enumerate(streamlit.session_state.messages):
    with streamlit.chat_message(message["role"]):
        streamlit.markdown(message["content"])

    # We need to keep track of the feedback our user has given.
    if message["role"] == "assistant":
        streamlit_feedback.streamlit_feedback(
            feedback_type="faces", on_submit=feedback_callback_factory(message["content"]), key=str(i)
        )

with streamlit.sidebar:
    streamlit.image("https://www.couchbase.com/wp-content/themes/couchbase-com/images/Logo-2000.svg")
    streamlit.divider()
    streamlit.markdown(
        "This travel agent is powered by Couchbase Agent Catalog. See "
        "[here](https://github.com/couchbaselabs/rosetta-example) for more details!"
    )

# Read in some user input...
if user_input := streamlit.chat_input():
    streamlit.session_state.messages.append({"role": "user", "content": user_input})
    with streamlit.chat_message("user"):
        streamlit.markdown(user_input)

    # ...then issue a request to the agent and emit the response.
    with streamlit.chat_message("assistant"):
        output_message = requests.post(
            streamlit.session_state.chat_url,
            params={"inp": user_input},
        )
        response_json = output_message.json()
        response = response_json["response"]
        streamlit.markdown(response)
    streamlit.session_state.messages.append({"role": "assistant", "content": response})
