"""Run the agent to conduct research and write a report.
"""
import datetime

from playwright.sync_api import sync_playwright

from config import check_openai_api_key
from agent.research_agent import ResearchAgent
from log.log import get_logger

LOGGER = get_logger(__name__)


def run_agent(task, report_type, agent, agent_role_prompt):
    """ Run the research agent to generate a report for the given task.
    The report is automatically written to a file in the outputs directory.
    """
    check_openai_api_key()

    start_time = datetime.datetime.now()

    with sync_playwright() as context:
        try:
            browser = context.chromium.launch(headless=False)
            page = browser.new_page()

            assistant = ResearchAgent(task, agent, agent_role_prompt, page)
            assistant.conduct_research()

            report, path = assistant.write_report(report_type)
            LOGGER.info("📝 Report written to: %s", path)
        finally:
            page.close()
            browser.close()

    end_time = datetime.datetime.now()
    LOGGER.info("End time: %s", end_time)
    LOGGER.info("Total run time: %s", end_time - start_time)

    return report, path
