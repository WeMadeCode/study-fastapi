import asyncio


async def ticker():
    print("  步骤 1")
    await asyncio.sleep(0)      # sleep(0) = "我主动让一下,立刻排回队列"
    print("  步骤 2")
    await asyncio.sleep(0)
    print("  步骤 3")


async def main():
    t = asyncio.create_task(ticker())
    await asyncio.sleep(0)
    print("main 插进来一步 1")
    await asyncio.sleep(0)
    print("main 插进来一步 2")
    await t


asyncio.run(main())
