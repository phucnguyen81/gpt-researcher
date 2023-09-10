from __future__ import annotations
import json
from time import sleep as time_sleep
from typing import Optional

import openai
from openai import OpenAIError
from langchain.adapters import openai as lc_openai
from colorama import Fore, Style

from agent.prompts import auto_agent_instructions
from config import Config
from log.log import get_logger

LOGGER = get_logger(__name__)
CFG = Config()

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
                LOGGER.info("Response: %s", paragraph)
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
    try:
        response = create_chat_completion(
            model=CFG.smart_llm_model,
            messages=[
                {"role": "system", "content": f"{auto_agent_instructions()}"},
                {"role": "user", "content": f"task: {task}"}],
            temperature=0,
        )

        return json.loads(response)
    except Exception as e:
        print(f"{Fore.RED}Error in choose_agent: {e}{Style.RESET_ALL}")
        return {"agent": "Default Agent",
                "agent_role_prompt": "You are an AI critical thinker research assistant. Your sole purpose is to write well written, critically acclaimed, objective and structured reports on given text."}


