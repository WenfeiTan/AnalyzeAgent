import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_agent_does_not_import_fastapi() -> None:
    agent_sources = (REPOSITORY_ROOT / "agent" / "src").rglob("*.py")

    assert all("fastapi" not in _imports(path) for path in agent_sources)


def test_backend_uses_only_agent_public_surface() -> None:
    backend_sources = (REPOSITORY_ROOT / "backend" / "src").rglob("*.py")

    for path in backend_sources:
        assert all(
            name == "analyze_agent" or not name.startswith("analyze_agent")
            for name in _imports(path)
        )


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names
