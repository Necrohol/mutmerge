#!/bin/bash
# mutmerge - Shell wrapper for the MutMerge Python script
# 1. Ensure the environment is 'Faked' correctly for Alpine
export PYTHONPATH="${PYTHONPATH:-.}"

# 2. Forward arguments to the Python Main
python3 mutmerge.py "$@"

# 3. If a build happened, trigger the Universal Indexer for the VPS
if [[ "$*" == *"--arch"* ]]; then
    echo ">>> Build cycle complete. Updating Public Binhost Index..."
    ./fix-binhost.sh
fi
