"""
Research assistant class that handles the research process
for a given question.
"""
import json
import uuid
import os
import re

from actions.web_scrape import summarize_page
from actions.web_search import web_search
from agent.llm_utils import chat_complete
from agent import prompts
from config import Config
from processing.text import (
    write_to_file,
    read_txt_files,
    write_md_to_pdf,
)
from utils.log import get_logger

LOGGER = get_logger(__name__)
CFG = Config()


class ResearchAgent:
    """ Research Agent handles the research process for a given question. """
    def __init__(self, question, agent, agent_role_prompt, page):
        """ Initializes the research assistant with the given question.
        """
        self.question = question
        self.agent = agent
        self.agent_role_prompt = (
            agent_role_prompt if agent_role_prompt
            else prompts.generate_agent_role_prompt(agent)
        )
        self.visited_urls = set()
        self.research_summary = ""
        self.directory_name = uuid.uuid4()
        os.makedirs("./outputs", exist_ok=True) # TODO: move to config
        self.dir_path = os.path.dirname(f"./outputs/{self.directory_name}/")
        self.page = page

    def conduct_research(self) -> str:
        """ Returns the research result if it already is available,
        otherwise conducts the research and returns the result.
        """
        self.research_summary = (
            read_txt_files(self.dir_path)
            if os.path.isdir(self.dir_path) else ""
        )

        if not self.research_summary:
            search_queries = self.create_search_queries()
            for query in search_queries:
                LOGGER.info("Running research for: %s", query)
                research_result = self.run_search_summary(query)
                self.research_summary += f"{research_result}\n\n"

        LOGGER.info(
            "Research summary: %s ...", self.research_summary[:100]
        )
        LOGGER.info(
            "Total research words: %s", len(self.research_summary.split())
        )

        return self.research_summary

    def create_search_queries(self) -> list[str]:
        """ Creates the search queries for the given question.
        Args: None
        Returns: list[str]: The search queries for the given question
        """
        search_queries_prompt = prompts.generate_search_queries_prompt(
            self.question
        )
        queries = self.call_agent(search_queries_prompt)
        LOGGER.info("Generated search queries: %s", queries)
        return json.loads(queries)

    def run_search_summary(self, query):
        """ Runs the search summary for the given query.
        Args: query (str): The query to run the search summary for
        Returns: str: The search summary for the given query
        """
        responses = self.scrape(query)
        result = "\n".join(responses)
        clean_query =  re.sub(r'\W+', '_', query)
        query_file = f"./outputs/{self.directory_name}/research-{clean_query}.txt"
        os.makedirs(os.path.dirname(query_file), exist_ok=True)
        write_to_file(query_file, result)
        return result

    def scrape(self, query):
        """ Returns a list of texts extracted from scraping the web for the
        given query.
        """
        search_results = web_search(query)
        if not search_results:
            LOGGER.warning("No search results found for: %s", query)
            return []

        new_search_urls = self.get_new_urls(search_results)

        LOGGER.info(
            "Browsing the following sites for relevant information on %s:\n%s",
            query,
            '\n'.join(new_search_urls)
        )

        # collect the results
        responses = [
            summarize_page(url, query, self.page) for url in new_search_urls
        ]
        return responses

    def get_new_urls(self, url_set_input) -> list[str]:
        """ Gets the new urls from the given url set.
        Args: url_set_input (set[str]): The url set to get the new urls from
        Returns: list[str]: The new urls from the given url set
        """
        new_urls = []
        for url in url_set_input:
            if url not in self.visited_urls:
                LOGGER.info("Adding source url to research: %s", url)
                self.visited_urls.add(url)
                new_urls.append(url)

        return new_urls

    def write_report(self, report_type):
        """ Writes the report for the given question.
        Args: None
        Returns: str: The report for the given question
        """
        report_type_func = prompts.get_report_by_type(report_type)
        LOGGER.info(
            "Writing report '%s' for research task: %s...",
            report_type, self.question
        )
        answer = self.call_agent(
            action=report_type_func(self.question, self.research_summary)
        )

        path = write_md_to_pdf(report_type, self.directory_name, answer)

        return answer, path

    def write_lessons(self):
        """ Writes lessons on essential concepts of the research.
        """
        concepts = self.create_concepts()
        for concept in concepts:
            lesson_prompt = prompts.generate_lesson_prompt(concept)
            answer = self.call_agent(lesson_prompt)
            write_md_to_pdf("Lesson", self.directory_name, answer)

    def create_concepts(self):
        """ Creates the concepts for the given question.
        Returns: list[str]: The concepts for the given question
        """
        concepts_prompt = prompts.generate_concepts_prompt(self.question, self.research_summary)
        result = self.call_agent(concepts_prompt)
        LOGGER.info(
            "Research is based on the following concepts: %s...", result
        )

        return json.loads(result)

    def call_agent(self, action):
        """ Gets the agent's response given an action to perform. The action
        should match the agent's role for a better response.

        NOTE: this task is more suitable for models with good reasoning
        capabilities. For example, GPT-4 is preferred over GPT-3 for this task.
        """
        messages = [{
            "role": "system",
            "content": self.agent_role_prompt
        }, {
            "role": "user",
            "content": action,
        }]
        answer = chat_complete(messages=messages, smart_model=True)
        return answer
