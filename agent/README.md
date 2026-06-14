# Analyze Agent Package

Reusable Python package for requirement analysis in the Asset Discovery
workflow. It owns the domain contracts, workflows, Gemini adapters, Knowledge
Base retriever boundary, confidence rules, and SQLite requirement revisions.

The package does not expose an HTTP server. Consumers should use the public
objects exported from `analyze_agent`.
