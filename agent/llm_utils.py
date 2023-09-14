""" Work with OpenAI API """
from __future__ import annotations
import json

from dotenv import dotenv_values
from langchain.adapters import openai as lc_openai
from openai import OpenAIError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_fixed,
)

from agent.prompts import auto_agent_instructions
from config import Config
from utils.fun import get_attr
from utils.log import get_logger

LOGGER = get_logger(__name__)
CFG = Config()
ENV = dotenv_values(".env")


def choose_agent(task: str) -> str:
    """ Determines what agent should be used
    Args:
        task (str): The research question the user asked
    Returns:
        agent - The agent that will be used
        agent_role_prompt (str): The prompt for the agent
    """
    messages = [
        {"role": "system", "content": f"{auto_agent_instructions()}"},
        {"role": "user", "content": f"task: {task}"},
    ]
    try:
        response = chat_complete(messages, smart_model=True)
        return json.loads(response)
    except Exception as error:
        LOGGER.info("Error in choose_agent: %s", error)
        return {
            "agent": "Default Agent",
            "agent_role_prompt": "You are an AI critical thinker research assistant. Your sole purpose is to write well written, critically acclaimed, objective and structured reports on given text."
        }


@retry(
    # retry on connection error
    retry=retry_if_exception_type(ConnectionError),
    # stop after 5 attempts or 180 seconds (3 mins) delay
    stop=(stop_after_attempt(5) | stop_after_delay(180)),
    # wait 10 seconds between attempts
    wait=wait_fixed(10),
)
def chat_complete(messages, smart_model=False, max_tokens=None, stream=False):
    """ Calls Chat Completion API and returns the text response.

    For example, the messages can be:
    [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {"role": "assistant", "content": "The Los Angeles Dodgers."},
        {"role": "user", "content": "Where was it played?"}
    ]
    """
    # Arguments to init a ChatOpenAI adapter instance
    args = {}

    provider = ENV.get("OPENAI_API_PROVIDER")
    if provider == "ChatOpenAI":
        model = (
            ENV.get("SMART_LLM_MODEL") if smart_model
            else ENV.get("FAST_LLM_MODEL")
        )
        args = {
            "provider": provider,
            "model": model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_tokens,
            "stream": stream,
        }
    elif provider == "AzureChatOpenAI":
        deployment_name = (
            ENV.get("AZURE_OPENAI_SMART_DEPLOYMENT") if smart_model
            else ENV.get("AZURE_OPENAI_FAST_DEPLOYMENT")
        )
        model = (
            ENV.get("AZURE_OPENAI_SMART_MODEL") if smart_model
            else ENV.get("AZURE_OPENAI_FAST_MODEL")
        )
        args = {
            "provider": "AzureChatOpenAI",
            "openai_api_type": ENV.get("AZURE_OPENAI_API_TYPE"),
            "openai_api_key": ENV.get("AZURE_OPENAI_API_KEY"),
            "openai_api_base": ENV.get("AZURE_OPENAI_ENDPOINT"),
            "deployment_name": deployment_name,
            "model": model,
            "openai_api_version": ENV.get("AZURE_OPENAI_API_VERSION"),
            "temperature": 0,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": stream,
        }
    else:
        raise ValueError(f"Unknown provider: {provider}")

    args = {k: v for k, v in args.items() if v is not None}
    try:
        result = lc_openai.ChatCompletion.create(**args)
    except OpenAIError as error:
        msg = "Failed to get response from OpenAI API"
        LOGGER.error(msg, exc_info=True)
        raise ConnectionError(msg) from error

    return get_attr(result, ["choices", 0, "message", "content"])
