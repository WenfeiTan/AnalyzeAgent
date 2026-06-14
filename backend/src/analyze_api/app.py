"""FastAPI application shell for the local demo backend."""

from analyze_agent import AnalyzeAgent
from fastapi import FastAPI


def create_app(*, agent: AnalyzeAgent | None = None) -> FastAPI:
    app = FastAPI(title="Analyze Agent API", version="0.1.0")
    app.state.agent = agent

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
