"""Launch a single agent — useful for debugging.

Usage:  python run_single.py monitor
        python run_single.py triage
        python run_single.py research
        python run_single.py drafting
        python run_single.py qa
        python run_single.py escalation
"""

import asyncio
import logging
import sys


AGENTS = {
    "monitor": "agents.monitor",
    "triage": "agents.triage",
    "research": "agents.research",
    "drafting": "agents.drafting",
    "qa": "agents.qa",
    "escalation": "agents.escalation",
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in AGENTS:
        print(f"Usage: python run_single.py <{'|'.join(AGENTS)}>")
        sys.exit(1)

    agent_name = sys.argv[1]
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s [{agent_name}] %(levelname)s %(message)s",
    )

    import importlib
    mod = importlib.import_module(AGENTS[agent_name])
    asyncio.run(mod.run())


if __name__ == "__main__":
    main()
