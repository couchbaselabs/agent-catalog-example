# Travel Agent Example

This directory contains all code required to run a sample travel agent whose tools and prompts are versioned with
Agent Catalog (`agentc`).

## Setup

### Agent Catalog Setup

1. Ensure that you have `python3.11` and `poetry` installed.

   ```bash
   python3 -m pip install poetry
   ```

2. Clone the `agent-catalog` repository.
   Make sure that you have an SSH key setup!

   ```bash
   git clone git@github.com:couchbaselabs/agent-catalog.git
   ```

3. Clone this repository outside the `agent-catalog` folder.

   ```bash
   cd ..
   git clone git@github.com:couchbaselabs/agent-catalog-example.git
   ```

4. Navigate to this directory, and install the dependencies from `pyproject.toml`.
   Be sure to modify the `$LOCATION_OF_LOCAL_AGENT_CATALOG_REPO` line to the location of the `agent-catalog` repository.
   Use `--with controlflow` to use the ControlFlow backend (more examples with other agent frameworks are coming soon!).

   ```bash
   cd agent-catalog-example/travel_agent
   sed -i -e 's|\$LOCATION_OF_LOCAL_AGENT_CATALOG_REPO|'"$PWD/../../agent-catalog"'|g' pyproject.toml
   poetry install --with controlflow
   ```

5. You should now have the `agentc` command line tool installed.
   Test your installation by running the `agentc` command (_the first run of this command will also compile libraries
   like Numpy, subsequent runs will be faster_).

   ```bash
   poetry shell
   agentc
   ```

6. Copy the `.env.example` file into a `.env` file, and update the environment variables appropriately.

   ```bash
   cp .env.example .env
   vi .env
   ```

For the remainder of the commands in this README, we assume the current working directory is `travel_agent`.

### Couchbase Setup

Now, we need some data in Couchbase!

1. Create a Couchbase instance (either locally or on Capella).
   You'll need a cluster with KV, N1QL, FTS, and Analytics (CBAS).
   We'll be using FTS for its vector index support and analytics to transform our agent activity.
   _If you have Docker installed, you can run the command below to quickly spin-up a Couchbase instance:
   ```bash
    mkdir -p .data/couchbase
    docker run -d --name my_couchbase \
      -p 8091-8096:8091-8096 -p 11210-11211:11210-11211 \
      -v "$(pwd)/.data/couchbase:/opt/couchbase/var" \
      couchbase
   ```
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
   For Capella instances, see the link
   [here](https://docs.couchbase.com/cloud/vector-search/create-vector-search-index-ui.html) for instructions on how
   to do so using the Capella UI (using the Search -> QUICK INDEX screen).

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
   agentc index src/resources/agent_c/tools
   agentc publish tool --bucket 'travel-sample'
   ```
   The local catalog, by default, will appear as `.agent_catalog/tool_catalog.json`.
   To publish these tools to a database and leverage the versioning capabilities of Agent Catalog, use the subsequent
   `publish` command after running the `index` command. _(Note that this `publish` step isn't necessary to continue with
   this tutorial.)_
3. Repeat this indexing step for the `prompts` folder, where all of our prompts are located.
   ```bash
   agentc index src/resources/agent_c/prompts
   agentc publish prompt --bucket 'travel-sample'
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
