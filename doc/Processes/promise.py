
from H5Gizmos import Html, serve
import asyncio

lyrics = """
Never gonna give you up
Never gonna let you down
Never gonna run around and desert you
Never gonna make you cry
Never gonna say goodbye
Never gonna tell a lie and hurt you
""".strip().split("\n")

async def task():
    greeting = Html("<h1>Hello</h1>")
    await greeting.show()
    for txt in lyrics:
        greeting.add(txt)
    await asyncio.sleep(0.2)
    greeting.shutdown()

serve(task())
