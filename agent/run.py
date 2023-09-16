"""Run the agent to conduct research and write a report.
"""
import datetime
from datetime import timedelta

from playwright.sync_api import sync_playwright

from config import check_openai_api_key
from agent.research_agent import ResearchAgent
from utils.log import get_logger

LOGGER = get_logger(__name__)


def run_agent(task, report_type, agent, agent_role_prompt):
    """ Run the research agent to generate a report for the given task.
    The reports are written to a sub-directory of the outputs directory.
    """
    check_openai_api_key()

    start_time = datetime.datetime.now()
    LOGGER.info("Start time: %s", start_time)

    with sync_playwright() as context:
        try:
            browser = context.chromium.launch(headless=False)
            page = browser.new_page()

            assistant = ResearchAgent(task, agent, agent_role_prompt, page)
            assistant.conduct_research()

            report, path = assistant.write_report(report_type)
            LOGGER.info("Report written to: %s", path)
        finally:
            page.close()
            browser.close()

    end_time = datetime.datetime.now()
    LOGGER.info("End time: %s", end_time)

    total_time = timedelta(
        seconds=int((end_time - start_time).total_seconds())
    )
    LOGGER.info("Total run time: %s", total_time)

    return report, path


def run_search(task, report_type, agent, agent_role_prompt):
    """ Run the search agent to generate a report for the given task.
    The reports are written to a sub-directory of the outputs directory.
    """
    check_openai_api_key()

    start_time = datetime.datetime.now()
    LOGGER.info("Start time: %s", start_time)

    with sync_playwright() as context:
        try:
            browser = context.chromium.launch(headless=False)
            page = browser.new_page()

            assistant = ResearchAgent(task, agent, agent_role_prompt, page)
            assistant.conduct_search()

            report, path = assistant.write_report(report_type)
            LOGGER.info("Report written to: %s", path)
        finally:
            page.close()
            browser.close()

    end_time = datetime.datetime.now()
    LOGGER.info("End time: %s", end_time)

    total_time = timedelta(
        seconds=int((end_time - start_time).total_seconds())
    )
    LOGGER.info("Total run time: %s", total_time)

    return report, path
