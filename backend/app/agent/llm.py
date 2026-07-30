from app import config


def get_llm():
    if config.LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=config.LLM_MODEL, api_key=config.ANTHROPIC_API_KEY)

    if config.LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(model=config.LLM_MODEL, api_key=config.GROQ_API_KEY)

    raise ValueError(f"Unknown LLM_PROVIDER: {config.LLM_PROVIDER}")
