import os
import rosetta.provider
import langchain_core.tools
import dotenv
import pathlib

# Load our OPENAI_API_KEY first...
dotenv.load_dotenv(
    pathlib.Path(__file__).parent.parent.parent / 'examples' / 'travel_agent' / '.env'
)

# ...before loading control flow.
import controlflow
import controlflow.tools


def test_flight_planning():
    tool_provider = rosetta.provider.Provider(
        decorator=langchain_core.tools.StructuredTool.from_function,
        secrets={
            'CB_CONN_STRING': os.getenv('CB_CONN_STRING'),
            'CB_USERNAME': os.getenv('CB_USERNAME'),
            'CB_PASSWORD': os.getenv('CB_PASSWORD')
        }
    )
    my_task = controlflow.Task(
        objective="Find a flight from HNL to SFO.",
        tools=tool_provider.get_tools_for('finding flights with one layover')
    )
    my_task.run()
    print(my_task.result)


def test_airport_checking():
    tool_provider = rosetta.Provider(
        decorator=langchain_core.tools.StructuredTool.from_function,
    )
    my_task = controlflow.Task(
        objective="Check if 'SFO' is a valid airport code.",
        tools=tool_provider.get_tools_for('checking valid airport codes')
    )
    my_task.run()
    print(my_task.result)


if __name__ == '__main__':
    test_flight_planning()
    test_airport_checking()