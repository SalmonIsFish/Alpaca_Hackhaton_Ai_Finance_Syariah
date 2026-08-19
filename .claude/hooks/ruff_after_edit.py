"""PostToolUse hook: ruff --fix + ruff format on whatever .py file Write/Edit just touched.

Only ever touches the file Claude just wrote -- never runs across the whole repo, so it
can't retroactively flag or reformat the ~100 pre-existing lint issues elsewhere in this
codebase. Reads the hook's stdin JSON directly rather than shelling out to jq (not
installed in this environment).
"""

import json
import subprocess
import sys
from pathlib import Path

RUFF = str(Path(__file__).resolve().parent.parent.parent / ".venv" / "Scripts" / "ruff.exe")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".py") or not Path(file_path).is_file():
        return 0

    subprocess.run([RUFF, "check", "--fix", "--quiet", file_path], check=False)
    subprocess.run([RUFF, "format", "--quiet", file_path], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
