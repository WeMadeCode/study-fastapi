import asyncio


async def slow_numbers():
    for i in range(3):
        await asyncio.sleep(1)
        yield i


async def main():
    print("开始接收：")
    async for n in slow_numbers():
        print(f"收到：{n}")


asyncio.run(main())
