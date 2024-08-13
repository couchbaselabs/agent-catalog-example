import os
import pathlib
import rosetta.core
import langchain_core.tools
import dotenv

# Load our OPENAI_API_KEY first...
dotenv.load_dotenv()

# ...before loading control flow.
import controlflow
import controlflow.tools


def test_flight_planning():
    tool_provider = rosetta.core.provider.Provider(
        catalog=rosetta.core.catalog.CatalogMem.load(pathlib.Path('.rosetta-catalog')),
        func_transform=langchain_core.tools.StructuredTool.from_function,
        secrets={
            'CB_CONN_STRING': lambda: os.getenv('CB_CONN_STRING'),
            'CB_USERNAME': lambda: os.getenv('CB_USERNAME'),
            'CB_PASSWORD': lambda: os.getenv('CB_PASSWORD')
        }
    )
    with tool_provider:
        my_task = controlflow.Task(
            objective="Find a flight from HNL to SFO.",
            tools=tool_provider.get_tools_for('finding flights with one layover')
        )
        my_task.run()
        print(my_task.result)


if __name__ == '__main__':
    test_flight_planning()
