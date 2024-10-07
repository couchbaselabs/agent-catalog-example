# Travel Agent Example
This directory contains all code required to run a sample travel agent whose tools and prompts are versioned with
Agent Catalog (`agentc`).

## Setup

### Agent Catalog Setup

1. Ensure that you have `python3.11` and `poetry` installed.
   ```bash
   python3 -m pip install poetry
   ```
2. Clone this repository -- make sure that you have an SSH key setup!
   ```bash
   git clone git@github.com:couchbaselabs/rosetta-example.git
   ```
3. Navigate to this directory, and install the dependencies from `pyproject.toml`.
   Use `--with controlflow` to use the ControlFlow backend (more examples with other agent frameworks are coming soon!).
   ```bash
   cd travel_agent
   poetry install --with controlflow
   ```
4. You should now have the `agentc` command line tool installed.
   Test your installation by running the `agentc` command (_the first run of this command downloads embedding models,
   subsequent runs will be faster_).
   ```bash
   poetry shell
   agentc
   ```
5. Copy the `.env.example` file into a `.env` file, and update the environment variables appropriately.
   ```bash
   cp .env.example .env
   vi .env
   ```

For the remainder of the commands in this README, we assume the current working directory is `travel_agent`.

### Couchbase Setup
Now, we need some data in Couchbase!
In the future, we will have a Docker image to simplify this setup.

1. Create a Couchbase instance (either locally or on Capella).
2. Load the `travel-sample` example in your Couchbase instance (under Settings -> Sample Buckets).
3. Register your Couchbase connection string, username, and password in the `.env` file.
4. Run the `ingest_blogs.py` setup script to generate embeddings and insert articles into a new
   `travel-sample.inventory.article` collection.
   ```bash
   python3 setup/ingest_blogs.py
   ```
5. Create a FTS index called `articles-index` for the `travel-sample.inventory.article` collection and the field `vec`.
   For non-Capella instances, we provide the helper script below.
   ```bash
   python3 setup/create_index.py
   ```
   For Capella instances, see the link [here](https://docs.couchbase.com/cloud/vector-search/create-vector-search-index-ui.html)
   for instructions on how to do so using the Capella UI (using the Search -> QUICK INDEX screen).


## Execution

We are now ready to start using Agent Catalog and ControlFlow to build agents!

1. In the `.env` file, add your OpenAI API key:
   ```
   OPENAI_API_KEY=[INCLUDE KEY HERE]
   ```
2. We have defined 24 tools (6 "real" tools and 18 "dummy" tools) in the `resources/tools` directory spread across files
   of multiple types (`.py`, `.sqlpp`, `.yaml`):
   ```bash
   ls resources/tools
   # blogs_from_interests.yaml
   # find_direct_flights.sqlpp
   # find_one_layover_flights.sqlpp
   # python_travel_tools.py
   # rewards_service.yaml
   ```
   We must now "index" our tools for Agent Catalog to serve to ControlFlow for use in its agentic workflows.
   Use the `index` command to create a local catalog, and point to where all of our tools are located.
   ```bash
   agentc index resources/tools --kind tool
   agentc publish --kind tool --bucket 'travel-sample'
   ```
   The local catalog, by default, will appear as `.agent_catalog/tool_catalog.json`.
   To publish these tools to a database and leverage the versioning capabilities of Agent Catalog, use the subsequent
   `publish` command after running the `index` command. _(Note that this `publish` step isn't necessary to continue with
   this tutorial.)_
3. Repeat this indexing step for the `prompts` folder, where all of our prompts are located.
   ```bash
   agentc index resources/prompts --kind prompt
   agentc publish --kind prompt --bucket 'travel-sample'
   ```
   Similarly, you are free to publish your prompts to a database with the same `publish` command (again, after
   the `index` command). _(Note that this `publish` step isn't necessary to continue with this tutorial.)_
4. Now that we have our tools available, our agent is ready to execute!
   Run the command below to start the agent server(s), a dummy REST server for managing travel rewards, and a
   Streamlit app for a ChatGPT-esque interface.
   Be sure to specify 'controlflow' in the script argument.
   ```bash
   ./quickstart.sh controlflow
   ```
5. Navigate to http://localhost:8501 and try out the app!
6. To stop the FastAPI + Prefect (if using ControlFlow) servers spawned as background processes in step 4, use Ctrl-C.
   If you still see left-over processes, run the command below.
   ```bash
   kill -9 $(ps -ef | grep -E 'agent_server.py|prefect|rewards_server.py|uvicorn' | grep -v 'grep' | awk '{print $2}')
   ```
