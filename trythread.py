from tgss.internal.thread import ThreadManager
import time
import asyncio

def consumer(msg):
    time.sleep(3)
    print(msg)
    

async def producer():
    for i in range(20):
        time.sleep(0.5)
        print("yielding: ", i)
        yield i

async def main():
    tm = ThreadManager(consumer)
    tm.run()

    async for msg in producer():
        tm.send(msg)

    print("Stopping")
    tm.stop()
    print("Stopped")

if __name__ == "__main__":
    asyncio.run(main())
    
    