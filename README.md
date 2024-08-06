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
   poetry install 
   ```
4. You should now have the `rosetta` command line tool installed.
   Test your installation by running the `rosetta` command.
   ```bash
   poetry shell
   rosetta
   ```

## For Developers

### Using Local `rosetta-core`

By default, `rosetta-example` will clone the `rosetta-core` repository and use the files specified in `master`.
For developers working on `rosetta-core` that want to see their changes reflected in `rosetta-example` without going
through `git`, perform the following:

1. Modify the `rosetta-core` line in `pyproject.toml` to point to your `rosetta-core` directory.
   ```toml
   # The core of Rosetta.
   # rosetta-core = { git = "git@github.com:couchbaselabs/rosetta-core.git" }
   rosetta-core = { path = "PATH TO ROSETTA-CORE REPO" }
   ```
2. From the top-level `rosetta-example` directory (not `rosetta-core`), update your Poetry environment.
   ```bash
   poetry update
   ```
3. Your Poetry environment for `rosetta-example` should now possess the `rosetta-core` files that are in your local
   `rosetta-core` directory.
   _Note that changes in `rosetta-core` aren't automatically reflected!
   You still need to run `poetry update` everytime a file in your local `rosetta-core` is changed._
