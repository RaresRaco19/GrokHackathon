#!/usr/bin/env bash
# Same as bin/desk.sh.
exec "$(cd "$(dirname "$0")" && pwd)/desk.sh" "$@"
