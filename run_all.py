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


async def run_agent_with_restart(agent_coro_func, name: str):
    log = logging.getLogger("run_all")
    while True:
        try:
            log.info(f"Starting agent: {name}")
            await agent_coro_func()
            log.warning(f"Agent '{name}' completed normally (unexpected). Restarting in 5s...")
        except asyncio.CancelledError:
            log.info(f"Agent '{name}' was cancelled.")
            break
        except Exception as e:
            log.error(f"Agent '{name}' crashed: {e}. Restarting in 5s...", exc_info=True)
        
        await asyncio.sleep(5)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    log = logging.getLogger("run_all")
    log.info("Starting all 6 agents...")

    tasks = [
        asyncio.create_task(run_agent_with_restart(monitor_run, "monitor"), name="monitor"),
        asyncio.create_task(run_agent_with_restart(triage_run, "triage"), name="triage"),
        asyncio.create_task(run_agent_with_restart(research_run, "research"), name="research"),
        asyncio.create_task(run_agent_with_restart(drafting_run, "drafting"), name="drafting"),
        asyncio.create_task(run_agent_with_restart(qa_run, "qa"), name="qa"),
        asyncio.create_task(run_agent_with_restart(escalation_run, "escalation"), name="escalation"),
    ]

    log.info("All 6 agents launched. Waiting for tasks...")
    
    # Wait for all tasks to complete (they run infinitely until cancelled)
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user.")
