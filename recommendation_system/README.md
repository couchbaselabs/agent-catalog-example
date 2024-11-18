# Recommendation system example

This directory contains all code required to run a recommendation system agent whose tools and prompts are versioned with
Agent Catalog (`agentc`).

## Setup

### Agent Catalog Setup

1. Ensure that you have `python3.12` and `poetry` installed.
   ```bash
   python3 -m pip install poetry
   ```
2. Clone this repository and `agent-catalog` -- make sure that you have an SSH key setup!
   ```bash
   git clone git@github.com:couchbaselabs/agent-catalog.git
   git clone git@github.com:couchbaselabs/agent-catalog-example.git
   ```
3. Navigate to this directory (`agent-catalog-example`), and install the dependencies from `pyproject.toml`.
   Be sure to modify the `$LOCATION_OF_LOCAL_AGENT_CATALOG_REPO` line to the location of the cloned `agent-catalog` repository.
   Use `--with controlflow` to use the ControlFlow backend (more examples with other agent frameworks are coming soon!).
   ```bash
   cd agent-catalog-example/travel_agent
   sed -i -e 's|\$LOCATION_OF_LOCAL_AGENT_CATALOG_REPO|'"$PWD/../../agent-catalog"'|g' pyproject.toml
   poetry install --with controlflow
   ```
   Tip: Running in verbose mode (with `-v` flag) would be beneficial if you are a windows user or the installation seems to be taking more time.
4. You should now have the `agentc` command line tool installed.
   Test your installation by running the `agentc` command (_the first run of this command will also compile libraries
   like Numpy, subsequent runs will be faster_).
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

1. Create a Couchbase instance (either locally or on Capella).
   You'll need a cluster with KV, N1QL, FTS, and Analytics (CBAS).
   We'll be using FTS for its vector index support and analytics to transform our agent activity.
   _If you have Docker installed, you can run the command below to quickly spin-up a Couchbase instance:
   ```bash
      docker run -d travel-example-db -p 8091-8096:8091-8096 -p 11210-11211:11210-11211 couchbase`
   ```
2. Create a bucket `ecommerce` with default config.
3. Register your Couchbase connection string, username, and password in the `.env` file.
4. Run the `setup/setup_script.sh` which does the following:
   i. Cleans the dataset present in `dataset/smartphones.csv` and push the data into Couchbase Cluster
   ii. Embed the field `display` so we can do vector search on top of it.
   iii. Creates vector index `mobile-index` over the display field.
   ```bash
   chmod +x setup/setup_script.sh
   ./setup/setup_script.sh
   ```

   For Capella instances, see the
   link [here](https://docs.couchbase.com/cloud/vector-search/create-vector-search-index-ui.html)
   for instructions on how to do so using the Capella UI (using the Search -> QUICK INDEX screen).

## Execution

We are now ready to start using Agent Catalog and ControlFlow to build agents!

1. In the `.env` file, add your OpenAI API key:
   ```
   OPENAI_API_KEY=[INCLUDE KEY HERE]
   ```
