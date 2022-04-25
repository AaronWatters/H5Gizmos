
from H5Gizmos import Html, serve

async def task():
    greeting = Html("<h1>Math facts</h1>")
    await greeting.show()
    greeting.add(Html("""
    <div>The <em>circumference</em> of a circle with radius 1, 2 &times; &pi;, is between 6 and 7.</div>
    """))
    greeting.add("That is, 6<6.28... & 7>6.28...")

serve(task())
