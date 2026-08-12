"""Test helper: run changed modules only."""

import subprocess
import sys
from pathlib import Path


def get_changed_py_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
    )
    files = [f for f in result.stdout.strip().split("\n") if f.endswith(".py")]
    return files


def find_test_for_module(module: str) -> str | None:
    name = Path(module).stem
    test_name = f"tests/unit/test_{name}.py"
    if Path(test_name).exists():
        return test_name
    return None


def main() -> int:
    changed = get_changed_py_files()
    if not changed:
        print("No Python files changed")
        return 0

    test_files: set[str] = set()
    for module in changed:
        test = find_test_for_module(module)
        if test:
            test_files.add(test)

    if not test_files:
        print("No test files match changed modules")
        return 0

    print(f"Running tests for: {', '.join(sorted(test_files))}")
    result = subprocess.run(["pytest", "-x", "-v", *sorted(test_files)])
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
