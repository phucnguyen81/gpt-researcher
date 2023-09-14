"""Text processing functions"""
from typing import Dict, Generator
import os
import urllib

from md2pdf.core import md2pdf

from agent.llm_utils import chat_complete
from config import Config

CFG = Config()


def split_text(text: str, max_length: int = 8192) -> Generator[str, None, None]:
    """Split text into chunks of a maximum length

    Args:
        text (str): The text to split
        max_length (int, optional): The maximum length of each chunk. Defaults to 8192.

    Yields:
        str: The next chunk of text

    Raises:
        ValueError: If the text is longer than the maximum length
    """
    paragraphs = text.split("\n")
    current_length = 0
    current_chunk = []

    for paragraph in paragraphs:
        if current_length + len(paragraph) + 1 <= max_length:
            current_chunk.append(paragraph)
            current_length += len(paragraph) + 1
        else:
            yield "\n".join(current_chunk)
            current_chunk = [paragraph]
            current_length = len(paragraph) + 1

    if current_chunk:
        yield "\n".join(current_chunk)


def summarize_text(text: str, question: str, page) -> str:
    """Summarize text using the OpenAI API

    Args:
        text (str): The text to summarize
        question (str): The question to ask the model
        page (Page): The page to scroll

    Returns:
        str: The summary of the text
    """
    if not text:
        return "Error: No text to summarize"

    summaries = []
    chunks = list(split_text(text))
    scroll_ratio = 1 / len(chunks)

    for idx, chunk in enumerate(chunks):
        if page:
            scroll_to_percentage(page, scroll_ratio * idx)

        messages = [create_message(chunk, question)]
        summary = chat_complete(messages=messages, smart_model=False)
        summaries.append(summary)

    combined_summary = "\n".join(summaries)
    messages = [create_message(combined_summary, question)]

    return chat_complete(messages=messages, smart_model=False)


def scroll_to_percentage(page, ratio: float) -> None:
    """ Scroll to a percentage of the given page
    Args:
        page (Page): the page to scroll
        ratio (float): the percentage to scroll to
    Raises:
        ValueError: If the ratio is not between 0 and 1
    """
    if ratio < 0 or ratio > 1:
        raise ValueError("Percentage should be between 0 and 1")
    page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {ratio});")


def create_message(chunk: str, question: str) -> Dict[str, str]:
    """ Create a message to answer a question or to summerize it.
    Args:
        chunk (str): The chunk of text to summarize
        question (str): The question to answer
    Returns:
        Dict[str, str]: The message to send to the chat completion
    """
    return {
        "role": "user",
        "content": f'"""{chunk}""" Using the above text, answer the following'
        f' question: "{question}" -- if the question cannot be answered using the text,'
        " simply summarize the text in depth. "
        "Include all factual information, numbers, stats etc if available.",
    }


def write_to_file(filename: str, text: str) -> None:
    """ Write text to a file
    Args:
        text (str): The text to write
        filename (str): The filename to write to
    """
    with open(filename, "w", encoding="utf-8") as file:
        file.write(text)


def write_md_to_pdf(task: str, directory_name: str, text: str) -> str:
    """ Write the task file in markdown to a pdf file. Return the path to
    the pdf file that has been encoded to be safely used in a url.
    """
    file_path = f"./outputs/{directory_name}/{task}"
    write_to_file(f"{file_path}.md", text)
    md_to_pdf(f"{file_path}.md", f"{file_path}.pdf")
    print(f"{task} written to {file_path}.pdf")

    encoded_file_path = urllib.parse.quote(f"{file_path}.pdf")

    return encoded_file_path


def read_txt_files(directory) -> str:
    """ Return a string read from all text files in the given directory
    """
    all_text = ''
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            with open(
                os.path.join(directory, filename), 'r', encoding='utf-8'
            ) as file:
                all_text += file.read() + '\n'
    return all_text


def md_to_pdf(input_file, output_file):
    """ Convert markdown input file to pdf output file
    """
    md2pdf(
        output_file,
        md_content=None,
        md_file_path=input_file,
        css_file_path=None,
        base_url=None,
    )
