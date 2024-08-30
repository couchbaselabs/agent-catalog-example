import dotenv
import langchain_core.tools
import langchain_openai
import os
import pathlib
import rosetta.langchain
import rosetta.provider

dotenv.load_dotenv(pathlib.Path(__file__).parent.parent.parent / "examples" / "travel_agent" / ".env")


def test_flight_planning():
    import controlflow.tools

    chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o")
    controlflow.default_agent = controlflow.Agent(
        name="Couchbase Travel Agent", model=rosetta.langchain.audit(chat_model)
    )

    tool_provider = rosetta.provider.Provider(
        decorator=langchain_core.tools.StructuredTool.from_function,
        secrets={
            "CB_CONN_STRING": os.getenv("CB_CONN_STRING"),
            "CB_USERNAME": os.getenv("CB_USERNAME"),
            "CB_PASSWORD": os.getenv("CB_PASSWORD"),
        },
    )
    my_task = controlflow.Task(
        objective="Find a flight from HNL to SFO.",
        tools=tool_provider.get_tools_for("finding flights with one layover"),
    )
    my_task.run()
    print(my_task.result)


def test_airport_checking():
    import controlflow

    chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o")
    controlflow.default_agent = controlflow.Agent(
        name="Couchbase Travel Agent", model=rosetta.langchain.audit(chat_model)
    )

    tool_provider = rosetta.Provider(
        decorator=langchain_core.tools.StructuredTool.from_function,
    )
    my_task = controlflow.Task(
        objective="Check if 'SFO' is a valid airport code.",
        tools=tool_provider.get_tools_for("checking valid airport codes"),
    )
    my_task.run()
    print(my_task.result)


def test_dest_recommendations():
    import controlflow

    chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o")
    controlflow.default_agent = controlflow.Agent(
        name="Couchbase Travel Agent", model=rosetta.langchain.audit(chat_model)
    )
    tool_provider = rosetta.Provider(
        decorator=langchain_core.tools.StructuredTool.from_function,
    )
    my_task = controlflow.Task(
        objective="Using the user's interest in beaches, find travel destinations using travel blogs.",
        tools=tool_provider.get_tools_for("reading travel blogs with user interests"),
    )
    my_task.run()
    print(my_task.result)


if __name__ == "__main__":
    test_flight_planning()
    test_airport_checking()
    test_dest_recommendations()
