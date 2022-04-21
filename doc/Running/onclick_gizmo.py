
from H5Gizmos import Html, serve

count = 0

async def task():
    greeting = Html("""
        <h1>
        Click this header to add one to the count
        </h2>
    """)
    await greeting.show()
    count_area = greeting.add("count area placeholder text")

    def add_one(*ignored):
        global count
        count += 1
        count_area.text("Count: " + str(count))

    greeting.set_on_click(add_one)

serve(task())
