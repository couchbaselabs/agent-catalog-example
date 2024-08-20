# rosetta-example

Sample agentic workflows built using Rosetta.

## Repository Setup

1. Ensure that you have `python3.11` and `poetry` installed.
   ```bash
   python3 -m pip install poetry
   ```
2. Clone this repository -- make sure that you have an SSH key setup!
   ```bash
   git clone git@github.com:couchbaselabs/rosetta-example.git
   ```
3. Install the dependencies from `pyproject.toml`.
   ```bash
   poetry install --no-root
   ```
4. You should now have the `rosetta` command line tool installed.
   Test your installation by running the `rosetta` command.
   ```bash
   poetry shell
   rosetta
   ```

## For Developers

### Using Local `rosetta` and `rosetta-core`

By default, `rosetta-example` will clone the `rosetta` repository and use the files specified in `master`.
For developers working on `rosetta-core` and/or `rosetta` that want to see their changes reflected in `rosetta-example`
without going through `git`, perform the following:

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
2. Remove the old `rosetta` (and `rosetta-core`) from your Python environment.
   ```bash
   pip uninstall rosetta rosetta-core
   ```
3. From `rosetta-example` (not `rosetta`), update your Poetry environment.
   ```bash
   poetry update
   ```
4. Your Poetry environment for `rosetta-example` should now possess the `rosetta` files that are in your local
   `rosetta` (and/or `rosetta-core`) directory.
   The `develop = true` attribute should signal to poetry that `rosetta` / `rosetta-core` is an "editable" package now,
   and allow  for `rosetta-example` to directly call `rosetta` / `rosetta-core` code (i.e., no duplicated source files).
