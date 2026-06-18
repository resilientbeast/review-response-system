import asyncio
from band import Agent
from band.core.simple_adapter import SimpleAdapter

class TestAdapter(SimpleAdapter):
    async def on_message(self, *args, **kwargs):
        pass

async def main():
    agent = Agent.from_config("monitor", adapter=TestAdapter())
    print("Agent dir:", dir(agent))
    # print runtime dir
    try:
        print("Runtime dir:", dir(agent.runtime))
    except Exception as e:
        print(e)

    # let's see if we can start it
    
asyncio.run(main())
