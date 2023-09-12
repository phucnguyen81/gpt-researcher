from __future__ import annotations
import json
from time import sleep as time_sleep
from typing import Optional

import openai
from openai import OpenAIError
from langchain.adapters import openai as lc_openai
from colorama import Fore, Style
from dotenv import dotenv_values

from agent.prompts import auto_agent_instructions
from config import Config
from log.log import get_logger

LOGGER = get_logger(__name__)
CFG = Config()
ENV = dotenv_values(".env")

openai.api_key = CFG.openai_api_key


def create_chat_completion(
    messages: list,  # type: ignore
    model: Optional[str] = None,
    temperature: float = CFG.temperature,
    max_tokens: Optional[int] = None,
    stream: Optional[bool] = False,
) -> str:
    """Create a chat completion using the OpenAI API
    Args:
        messages (list[dict[str, str]]): The messages to send to the chat completion
        model (str, optional): The model to use. Defaults to None.
        temperature (float, optional): The temperature to use. Defaults to 0.9.
        max_tokens (int, optional): The max tokens to use. Defaults to None.
        stream (bool, optional): Whether to stream the response. Defaults to False.
    Returns:
        str: The response from the chat completion
    """

    # validate input
    if model is None:
        raise ValueError("Model cannot be None")
    if max_tokens is not None and max_tokens > 8001:
        raise ValueError(f"Max tokens cannot be more than 8001, but got {max_tokens}")

    # create response
    try:
        response = send_chat_completion_request(
            messages, model, temperature, max_tokens, stream
        )
        return response
    except OpenAIError as error:
        msg = "Failed to get response from OpenAI API"
        LOGGER.error(msg)
        raise RuntimeError(msg) from error


def send_chat_completion_request(
    messages, model, temperature, max_tokens, stream
):
    # FIXME: find a better way to stay within rate limit
    time_sleep(30) # crude way to stay within rate limit
    if not stream:
        result: any = lc_openai.ChatCompletion.create(
            model=model, # Change model here to use different models
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            provider="ChatOpenAI", # Change provider here to use a different API
        )
        return result["choices"][0]["message"]["content"]
    else:
        return stream_response(model, messages, temperature, max_tokens)


def stream_response(model, messages, temperature, max_tokens):
    paragraph = ""
    response = ""
    LOGGER.info("Streaming response...")

    for chunk in lc_openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        provider="ChatOpenAI",
        stream=True,
    ):
        content = chunk["choices"][0].get("delta", {}).get("content")
        if content is not None:
            response += content
            paragraph += content
            if "\n" in paragraph:
                LOGGER.debug("Response: %s", paragraph)
                paragraph = ""

    LOGGER.info("streaming response complete")
    return response


def choose_agent(task: str) -> str:
    """Determines what agent should be used
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
        # response = create_chat_completion(
        #     model=CFG.smart_llm_model,
        #     messages=[
        #         {"role": "system", "content": f"{auto_agent_instructions()}"},
        #         {"role": "user", "content": f"task: {task}"}],
        #     temperature=0,
        # )

        return json.loads(response)
    except Exception as e:
        print(f"{Fore.RED}Error in choose_agent: {e}{Style.RESET_ALL}")
        return {"agent": "Default Agent",
                "agent_role_prompt": "You are an AI critical thinker research assistant. Your sole purpose is to write well written, critically acclaimed, objective and structured reports on given text."}


def chat_complete(messages, smart_model=False, max_tokens=None, stream=False):
    """ Calls Chat Completion API and returns the text response.

    For example, the messages can be:
    [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
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
        LOGGER.error(msg)
        raise RuntimeError(msg) from error

    return get_attr(result, ["choices", 0, "message", "content"])


def get_attr(obj, attrs):
    """ Get a nested attribute from an object given the attribute chain
    For example, to get the text from an OpenAI chat completion response:
    text = get_attr(response , ["choices", 0, "message", "content"])
    """
    for attr in attrs:
        obj = getattr(obj, attr, default={})
    return obj
