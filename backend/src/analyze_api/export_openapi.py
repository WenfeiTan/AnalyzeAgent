"""Export the Backend OpenAPI document for external client generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from analyze_api.app import create_app


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m analyze_api.export_openapi OUTPUT_PATH")
    output_path = Path(sys.argv[1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
