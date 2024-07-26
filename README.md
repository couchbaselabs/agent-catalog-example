# rosetta-sample

A sample agentic workflow built using Rosetta.

## Rosetta Setup

Before we start, we need the `rosetta-core` package.

1. Head over to the [rosetta-core](https://github.com/couchbaselabs/rosetta-core) repository to generate a `.whl`
   file (in the future, we will host `rosetta` on PyPI).
2. Install following requirements to run the examples in this repository.
   ```bash
   python3 -m pip install -r requirements.txt
   
   # Install the .whl files from the previous step...
   python3 -m pip install rosetta_core-*.*.*-py3-*-any.whl 
   ```
3. Test your installation by running the `rosetta init` command.
   ```bash
   rosetta init
   ```

## Travel Example Setup

Now, we need some data in Couchbase!

1. Create a Couchbase instance (either locally or on Capella).
2. Load the `travel-sample` example in your Couchbase instance (under Settings -> Sample Buckets).
3. Register your Couchbase connection string, username, and password in the `.env` file.
4. Create a new collection called `travel-sample.inventory.article`.
   ```sql
   CREATE COLLECTION `travel-sample`.`inventory`.`article` IF NOT EXISTS;
   ```
5. Run the `ingest_blog_data.py` setup script to generate embeddings and insert articles into the 
   `travel-sample.inventory.article` collection above.
   ```bash
   python3 setup_travel_data.py
   ```   
6. Create a FTS index for the `travel-sample.inventory.article` collection and the field `vec`.
   See the link [here](https://docs.couchbase.com/cloud/vector-search/create-vector-search-index-ui.html) for
   instructions on how to do so using the UI (using the Search -> QUICK INDEX screen).

## Travel Example Agent

We are now ready to start using Rosetta and ControlFlow to build agents!

1. In the `.env` file, add your OpenAI API key:
   ```
   OPENAI_API_KEY=[INCLUDE KEY HERE]
   ```
2. We have defined 22 tools (4 "real" tools and 18 "dummy" tools) in the `travel_tools` directory spread across files 
   of multiple types (`.py`, `.sqlpp`, `.yaml`):
   ```bash
   ls travel_tools
   # python_travel_tools.py
   # blogs_from_interests.yaml
   # direct_flights.sqlpp
   # one_layover_flights.sqlpp
   ```
   We must now "index" our tools for Rosetta to serve to ControlFlow for use in its agentic workflows.
   Use the `register` command to create a local catalog, and point to where all of our tools are located.
   ```bash
   rosetta index travel_tools
   ```
   The local catalog, by default, will appear as `.out/catalog.json`.
   In the future, there will be an option to register / add your tools to Capella.
3. Now that we have our tools available, our agent is ready to execute!
   Run the command below to start the agent server (via FastAPI and ControlFlow).
   ```bash
   fastapi run my_travel_agent.py
   ```
4. With our agent up and running, let's now spin up our application to interact with our agent using a ChatGPT-esque 
   interface (via Streamlit).
   ```bash
   streamlit run my_travel_app.py
   ```