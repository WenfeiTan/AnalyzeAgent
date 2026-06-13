from analyze_agent.config import load_settings


def main() -> None:
    settings = load_settings(require_api_key=True)
    print(
        "Analyze Agent configuration is valid "
        f"(model={settings.model}, log_level={settings.log_level})."
    )


if __name__ == "__main__":
    main()

