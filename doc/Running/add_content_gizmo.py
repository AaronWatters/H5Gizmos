
from H5Gizmos import Html, serve

async def task():
    greeting = Html("""
        <img src="dog.png"/>
    """)
    greeting.add_content("example_folder/dog.png")
    await greeting.show()
    info = greeting.add("A dog.")

serve(task())
