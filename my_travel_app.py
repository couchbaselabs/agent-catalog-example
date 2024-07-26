import http
import streamlit
import requests
import dotenv
import os

# Our first-time actions: initialize a conversation with our agent.
if 'thread_id' not in streamlit.session_state:
    dotenv.load_dotenv()

    # Determine our agent endpoints.
    agent_server_base = os.getenv('AGENT_CONN_STRING')
    start_url = agent_server_base + '/start'
    chat_url = agent_server_base + '/chat'

    # Here, we make our initial call to our agent.
    response = requests.post(start_url)
    if response.status_code != http.HTTPStatus.OK:
        raise EnvironmentError('Cannot connect to agent server!')
    response_json = response.json()

    # Save our thread_id and the initial messages.
    streamlit.session_state.thread_id = response_json['thread_id']
    streamlit.session_state.chat_url = chat_url + '/' + response_json['thread_id']
    streamlit.session_state.messages = [
        {
            'role': 'assistant',
            'content': response_json['initial_message']
        }
    ]

streamlit.title('Couchbase Travel Agent')

# On refresh, we should not lose any of our messages.
for message in streamlit.session_state.messages:
    with streamlit.chat_message(message['role']):
        streamlit.markdown(message['content'])

# Read in some user input...
if user_input := streamlit.chat_input():
    streamlit.session_state.messages.append({
        'role': 'user', 'content': user_input
    })
    with streamlit.chat_message('user'):
        streamlit.markdown(user_input)

    # ...then issue a request to the agent and emit the response.
    with streamlit.chat_message('assistant'):
        output_message = requests.post(
            streamlit.session_state.chat_url,
            json={'inp': user_input},
        )
        response = streamlit.write(output_message)
    streamlit.session_state.messages.append({
        'role': 'assistant',
        'content': response
    })
