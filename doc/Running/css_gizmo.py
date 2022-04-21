
from H5Gizmos import Html, serve
import asyncio

async def task():
    greeting = Html("""
        <h1>
        Warning: This interface is also annoying!
        </h1>
    """)
    await greeting.show()
    info = greeting.add("info area placeholder text")
    for i in range(60):
        greeting.css(color="blue")
        greeting.css({"background-color": "yellow"})
        info.text("blue/yellow " + str(i))
        await asyncio.sleep(1)
        greeting.css(color="green")
        greeting.css({"background-color": "magenta"})
        info.text("green/magenta " + str(i))
        await asyncio.sleep(1)
    greeting.add("All done!")

serve(task())
