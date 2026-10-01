#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
    printf '%s\n' 'Set up the virtual environment first; see README.md.'
    exit 1
fi
# Load this checkout even when a copied editable-install path is unavailable.
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
exec .venv/bin/python -m bluebell "$@"
