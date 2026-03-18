import asyncio
from worker import worker


async def test():
    worker.startup()
    print("health:", worker.health())

    print("\ntest query...")
    async for event in worker.handle_query(query="what is 2 + 2?"):
        t = event["type"]
        if t == "token":
            print(event["token"], end="", flush=True)
        elif t == "done":
            print("\ndone ✓")
        elif t == "error":
            msg = event.get("message", "unknown")
            print(f"error: {msg}")


asyncio.run(test())
