
from H5Gizmos import Html, serve
import asyncio

async def task():
    greeting = Html("""
        <h1>
        Warning: This interface is annoying!
        </h1>
    """)
    greeting.embedded_css("""
    .normal {
        color: blue;
        background-color: cornsilk;
    }
    .highlight {
        color: red;
        background-color: yellow;
    }
    """)
    await greeting.show()
    greeting.addClass("normal")
    greeting.add("sleeping 10 seconds")
    await asyncio.sleep(10)
    greeting.add('now highlignting')
    greeting.removeClass("normal")
    greeting.addClass("highlight")

serve(task())
