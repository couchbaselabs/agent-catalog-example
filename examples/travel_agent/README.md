# Travel Agent Example

## Setup

Now, we need some data in Couchbase!
In the future, we will have a Docker image to simplify this setup.

1. Create a Couchbase instance (either locally or on Capella).
2. Load the `travel-sample` example in your Couchbase instance (under Settings -> Sample Buckets).
3. Register your Couchbase connection string, username, and password in the `.env` file.
4. Create a new collection called `travel-sample.inventory.article`.
   ```sql
   CREATE COLLECTION `travel-sample`.`inventory`.`article` IF NOT EXISTS;
   ```
5. Run the `ingest_blogs.py` setup script to generate embeddings and insert articles into the
   `travel-sample.inventory.article` collection above.
   ```bash
   cd examples/travel_agent
   python3 setup/ingest_blogs.py
   ```
6. Create a FTS index for the `travel-sample.inventory.article` collection and the field `vec`.
   See the link [here](https://docs.couchbase.com/cloud/vector-search/create-vector-search-index-ui.html) for
   instructions on how to do so using the UI (using the Search -> QUICK INDEX screen).

## Execution

We are now ready to start using Rosetta and ControlFlow to build agents!

1. In the `.env` file, add your OpenAI API key:
   ```
   OPENAI_API_KEY=[INCLUDE KEY HERE]
   ```
2. We have defined 24 tools (6 "real" tools and 18 "dummy" tools) in the `travel_tools` directory spread across files
   of multiple types (`.py`, `.sqlpp`, `.yaml`):
   ```bash
   ls tools
   # blogs_from_interests.yaml
   # find_direct_flights.sqlpp
   # find_one_layover_flights.sqlpp
   # python_travel_tools.py
   # rewards_service.yaml
   ```
   We must now "index" our tools for Rosetta to serve to ControlFlow for use in its agentic workflows.
   Use the `index` command to create a local catalog, and point to where all of our tools are located.
   ```bash
   cd examples/travel_agent
   rosetta index tools
   ```
   The local catalog, by default, will appear as `.out/tool_catalog.json`.
   In the future, there will be an option to register / add your tools to Capella.
3. Now that we have our tools available, our agent is ready to execute!
   Run the command below to start the agent server (via FastAPI and ControlFlow) and a dummy REST server for managing
   travel rewards.
   ```bash
   cd examples/travel_agent
   fastapi run services/agent_server.py --port 10000
   fastapi run services/rewards_server.py --port 10001
   ```
4. With our servers up and running, let's now spin up a basic application to interact with our agent using a
   ChatGPT-esque interface (via Streamlit).
   ```bash
   cd examples/travel_agent
   streamlit run app.py
   ```