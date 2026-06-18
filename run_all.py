"""Launch all 6 agents concurrently.

Usage:  python run_all.py
"""

import asyncio
import logging

from agents.monitor import run as monitor_run
from agents.triage import run as triage_run
from agents.research import run as research_run
from agents.drafting import run as drafting_run
from agents.qa import run as qa_run
from agents.escalation import run as escalation_run


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    log = logging.getLogger("run_all")
    log.info("Starting all 6 agents...")

    tasks = [
        asyncio.create_task(monitor_run(),     name="monitor"),
        asyncio.create_task(triage_run(),      name="triage"),
        asyncio.create_task(research_run(),    name="research"),
        asyncio.create_task(drafting_run(),    name="drafting"),
        asyncio.create_task(qa_run(),          name="qa"),
        asyncio.create_task(escalation_run(),  name="escalation"),
    ]

    log.info("All 6 agents launched. Waiting for tasks...")

    # If any agent crashes, log it but keep the rest running
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    for task in done:
        if task.exception():
            log.error(f"Agent '{task.get_name()}' crashed: {task.exception()}")

    # Cancel remaining tasks on first crash
    for task in pending:
        task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
