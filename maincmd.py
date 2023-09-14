""" Command line version of the main app. """
from agent.llm_utils import choose_agent
from agent.run import run_agent
from utils.log import get_logger

LOGGER = get_logger(__name__)

# Set task and report_type
TASK = "OpenAI applications and features"
REPORT_TYPE = "research_report"

# Choose an agent
AGENT = choose_agent(task=TASK)
AGENT_NAME = AGENT['agent']
AGENT_PROMPT = AGENT['agent_role_prompt']
LOGGER.info("Chosen agent: %s, agent prompt: %s", AGENT_NAME, AGENT_PROMPT)

run_agent(
    task=TASK,
    report_type=REPORT_TYPE,
    agent=AGENT_NAME,
    agent_role_prompt=AGENT_PROMPT,
)
