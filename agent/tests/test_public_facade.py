from analyze_agent import AnalyzeAgent, AnalyzeAgentRuntime


def test_public_facade_wraps_runtime() -> None:
    runtime = object.__new__(AnalyzeAgentRuntime)

    facade = AnalyzeAgent(runtime)

    assert facade._runtime is runtime
