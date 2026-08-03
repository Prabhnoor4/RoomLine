from langchain_litellm import ChatLiteLLM

from app import config


def get_llm():
    return ChatLiteLLM(model=config.LLM_MODEL)
