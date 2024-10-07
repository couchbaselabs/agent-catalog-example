# agent-catalog-example

Sample agentic workflows built using Rosetta.

## For Users

Navigate to the specific example (e.g., `travel_agent`) you are interested in! :-)

## For Developers

### Setting up Pre-Commit

To set up `pre-commit` and reap all the benefits of code formatting, linting, automatic `poetry` lock generation, etc...
execute the following command:

```bash
pip install pre-commit
pre-commit install
```

### Using Local `rosetta`, `rosetta-core`, and `rosetta-lc`

By default, `rosetta-example` will clone the `rosetta` repository and use the files specified in `master`.
For developers working on `rosetta-core` / `rosetta` / `rosetta-lc` that want to see their changes reflected in
`rosetta-example` without going through `git`, perform the following:

1. Modify the `rosetta` line in `pyproject.toml` to point to your `rosetta` directory.
   ```toml
   # The core of Rosetta.
   # rosetta = { git = "git@github.com:couchbaselabs/rosetta-core.git" }
   rosetta = { path = PATH_TO_LOCAL_ROSETTA, develop = true }
   ```
   If you want a local version of `rosetta-core`, add the line below:
   ```toml
   rosetta-core = { path = PATH_TO_LOCAL_ROSETTA_CORE, develop = true }
   ```
   If you want a local version of `rosetta-lc`, add the line below:
   ```toml
   rosetta-lc = { path = PATH_TO_LOCAL_ROSETTA_LC, develop = true }
   ```
2. Remove the old `rosetta` (and/or `rosetta-core` and/or `rosetta-lc`) from your Python environment.
   ```bash
   pip uninstall rosetta rosetta-core rosetta-lc
   ```
3. From `rosetta-example` (not `rosetta`), update your Poetry environment.
   ```bash
   poetry update
   ```
4. Your Poetry environment for `rosetta-example` should now possess the `rosetta` files that are in your local
   `rosetta` (and/or `rosetta-core` and/or `rosetta-lc`) directory.
   The `develop = true` attribute should signal to poetry that `rosetta` / `rosetta-core` / `rosetta-lc` is an
   "editable" package now, and allow for `rosetta-example` to directly call `rosetta` / `rosetta-core` / `rosetta-lc`
   code (i.e., no duplicated source files).
