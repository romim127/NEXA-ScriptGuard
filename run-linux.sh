#!/usr/bin/env bash
set -eu

project_dir="$(cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_path=""
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) python_in_venv="Scripts/python.exe" ;;
    *) python_in_venv="bin/python" ;;
esac

if [[ -x "$project_dir/.venv/$python_in_venv" ]]; then
    python_path="$project_dir/.venv/$python_in_venv"
elif [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/$python_in_venv" ]]; then
    python_path="$(cd -- "$VIRTUAL_ENV" && pwd)/$python_in_venv"
else
    printf '%s\n' 'NEXA ScriptGuard: create .venv or activate a compatible virtual environment.' \
        'See docs/development/SETUP.md for installation commands.' >&2
    exit 1
fi

cd -- "$project_dir"
exec "$python_path" -m nexa_scriptguard.gui "$@"
