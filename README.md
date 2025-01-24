**This repo has been deprecated. Please refer to the mono-repo examples folder [here](https://github.com/couchbaselabs/agent-catalog/tree/master/templates/agents/with_controlflow)**.

# agent-catalog-example

Sample agentic workflows built using Couchbase Agent Catalog.

## For Users

Navigate to the specific example (e.g., `travel_agent`) you are interested in! :-)
In the future, we will have more examples for you to explore.

## For Developers

### Setting up Pre-Commit

To set up `pre-commit` and reap all the benefits of code formatting, linting, automatic `poetry` lock generation, etc...
execute the following command:

```bash
pip install pre-commit
pre-commit install
```

### Using Local `agentc`

By default, all examples in `agentc-example` will clone the `agent-catalog` repository and use the files specified in
`master` (specifically, `libs/agentc`).
For developers working on any of the `agentc` packages that want to see their changes reflected in `agentc-example`
without going through `git`, perform the following:

1. In the specific example you want to run (e.g., `travel_agent`), modify the `[tool.poetry.dependencies.agentc]`
   section in `pyproject.toml` to point to your cloned `agent-catalog` directory.
   Specifically, you'll need to comment out the "git" and "subdirectories" line and comment out the "path" line.
   Substitute `$LOCATION_OF_LOCAL_AGENT_CATALOG_REPO` accordingly.
   ```toml
   # The agentc project (the front-facing parts)!
   [tool.poetry.dependencies.agentc]
   # git = "git@github.com:couchbaselabs/agent-catalog.git"
   # subdirectory = "libs/agentc"
   path = "$LOCATION_OF_LOCAL_AGENT_CATALOG_REPO/libs/agentc"
   extras = ["langchain"]
   develop = true
   ```
2. Now update your Poetry environment.
   ```bash
   poetry update
   ```
   Tip: Running in verbose mode (with `-v` flag) would be beneficial if you are a windows user or the installation seems to be taking more time.

Your Poetry environment should now possess the `agentc-catalog` files in `$LOCATION_OF_LOCAL_AGENT_CATALOG_REPO`.
