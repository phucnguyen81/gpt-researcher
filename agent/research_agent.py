"""
Research assistant class that handles the research process
for a given question.
"""
from io import StringIO
import json
import uuid
import os
import re

from actions.web_scrape import sync_browse
from actions.web_search import web_search
from processing.text import \
    write_to_file, \
    create_message, \
    create_chat_completion, \
    read_txt_files, \
    write_md_to_pdf
from config import Config
from agent import prompts

from log.log import get_logger

LOGGER = get_logger(__name__)
CFG = Config()


class ResearchAgent:
    """ Research Agent handles the research process for a given question. """
    def __init__(self, question, agent, agent_role_prompt, page):
        """ Initializes the research assistant with the given question.
        Args: question (str): The question to research
        Returns: None
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
        self.dir_path = os.path.dirname(f"./outputs/{self.directory_name}/")
        self.page = page


    def summarize(self, text, topic):
        """ Summarizes the given text for the given topic.
        Args: text (str): The text to summarize
                topic (str): The topic to summarize the text for
        Returns: str: The summarized text
        """
        messages = [create_message(text, topic)]
        LOGGER.info("Summarizing text for query: %s", text)

        return create_chat_completion(
            model=CFG.fast_llm_model,
            messages=messages,
        )

    def get_new_urls(self, url_set_input):
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

    def call_agent(self, action, stream=False):
        messages = [{
            "role": "system",
            "content": self.agent_role_prompt
        }, {
            "role": "user",
            "content": action,
        }]
        answer = create_chat_completion(
            model=CFG.smart_llm_model,
            messages=messages,
            stream=stream,
        )
        return answer

    def create_search_queries(self):
        """ Creates the search queries for the given question.
        Args: None
        Returns: list[str]: The search queries for the given question
        """
        queries = self.call_agent(prompts.generate_search_queries_prompt(self.question))
        LOGGER.info("Conducting research based on the following queries: %s...", queries)
        return StringIO(queries).readlines()

    def sync_search(self, query):
        search_results = json.loads(web_search(query))
        new_search_urls = self.get_new_urls([url.get("href") for url in search_results])

        LOGGER.info("Browsing the following sites for relevant information: %s...", new_search_urls)

        # collect the results
        responses = [
            sync_browse(url, query, self.page) for url in new_search_urls
        ]
        return responses

    def run_search_summary(self, query):
        """ Runs the search summary for the given query.
        Args: query (str): The query to run the search summary for
        Returns: str: The search summary for the given query
        """
        LOGGER.info("🔎 Running research for '%s'...", query)

        responses = self.sync_search(query)

        result = "\n".join(responses)
        clean_query =  re.sub(r'\W+', '_', query)
        query_file = f"./outputs/{self.directory_name}/research-{clean_query}.txt"
        os.makedirs(os.path.dirname(query_file), exist_ok=True)
        write_to_file(query_file, result)
        return result

    def conduct_research(self):
        """ Conducts the research for the given question.
        Args: None
        Returns: str: The research for the given question
        """

        self.research_summary = read_txt_files(self.dir_path) if os.path.isdir(self.dir_path) else ""

        if not self.research_summary:
            search_queries = self.create_search_queries()
            for query in search_queries:
                research_result = self.run_search_summary(query)
                self.research_summary += f"{research_result}\n\n"

        LOGGER.info("Total research words: %s", len(self.research_summary.split(' ')))

        return self.research_summary


    def create_concepts(self):
        """ Creates the concepts for the given question.
        Args: None
        Returns: list[str]: The concepts for the given question
        """
        result = self.call_agent(prompts.generate_concepts_prompt(self.question, self.research_summary))
        LOGGER.info("🧠 I will research based on the following concepts: %s...", result)

        return json.loads(result)

    def write_report(self, report_type):
        """ Writes the report for the given question.
        Args: None
        Returns: str: The report for the given question
        """
        report_type_func = prompts.get_report_by_type(report_type)
        LOGGER.info("✍️ Writing %s for research task: %s...", report_type, self.question)
        answer = self.call_agent(
            report_type_func(self.question, self.research_summary),
            stream=True
        )

        path = write_md_to_pdf(report_type, self.directory_name, answer)

        return answer, path

    def write_lessons(self):
        """ Writes lessons on essential concepts of the research.
        """
        concepts = self.create_concepts()
        for concept in concepts:
            answer = self.call_agent(prompts.generate_lesson_prompt(concept), stream=True)
            write_md_to_pdf("Lesson", self.directory_name, answer)
