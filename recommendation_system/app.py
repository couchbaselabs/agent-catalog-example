import agentc
import controlflow as cf
import controlflow.events
import controlflow.events.events
import controlflow.orchestration
import controlflow.tools
import dotenv
import os

dotenv.load_dotenv()

# provider class instantiation
provider = agentc.Provider(
    decorator=lambda t: controlflow.tools.Tool.from_function(t.func),
    secrets={
        "CB_CONN_STRING": os.getenv("CB_CONN_STRING"),
        "CB_USERNAME": os.getenv("CB_USERNAME"),
        "CB_PASSWORD": os.getenv("CB_PASSWORD"),
    },
)


@cf.flow
def smartphone_recommendation_workflow():
    ram = cf.Task(
        "Get the desired ram from the user",
        interactive=True,
        result_type=int,
        prompt=provider.get_prompt_for(query="Get the desired ram from the user").prompt,
    )

    storage = cf.Task(
        "Get the desired storage from the user",
        interactive=True,
        result_type=int,
        prompt=provider.get_prompt_for(query="Get the desired storage from the user").prompt,
    )

    rating = cf.Task(
        "Get the desired rating from the user",
        interactive=True,
        result_type=int,
        prompt=provider.get_prompt_for(query="Get the desired rating from the user").prompt,
    )

    price = cf.Task(
        "Get the desired price (budget) from the user",
        interactive=True,
        result_type=int,
        prompt=provider.get_prompt_for(query="Get the desired price from the user").prompt,
    )

    filtering_level_1 = cf.Task(
        "Get list of relevant mobiles based on the user expectations",
        result_type=list[str],
        depends_on=[ram, storage, rating, price],
        tools=provider.get_tools_for("Get the relevant mobiles based on the user expectations"),
        prompt=provider.get_prompt_for("Get list of relevant mobiles based on the user expectations").prompt,
    )

    display = cf.Task("Get the desired display requirement from the user", interactive=True, result_type=str)

    filtering_level_2 = cf.Task(
        "Get mobiles which are close to the display description given by the user",
        depends_on=[display],
        result_type=list[str],
        tools=provider.get_tools_for("Get mobiles which are close to the display description given by the user"),
    )

    most_relevant_smartphone = cf.Task(
        "Select one mobile which is most relevant from the results given by filtering_stage_1 and filtering_stage_2",
        depends_on=[filtering_level_1, filtering_level_2],
        result_type=str,
        tools=provider.get_tools_for(
            "get the first word which is present in listB (filtering_stage_1) but also present in listA (filtering_stage_2)"
        ),
    )

    link = cf.Task(
        "Get the amazon buy link of the mobile phone",
        tools=provider.get_tools_for("Get the amazon buy link of the mobile phone"),
        depends_on=[most_relevant_smartphone],
    )
    return link.run()


workflow = smartphone_recommendation_workflow()
print(f"The most relevant phone based on your current requirements is {workflow}\n")
