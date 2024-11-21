#!/bin/bash

# Get the directory of the current script
DIR="$(dirname "$(realpath "$0")")"

# Run each Python file sequentially
python "$DIR/data_setup.py"
python "$DIR/vectorize.py"
python "$DIR/create_index.py"
