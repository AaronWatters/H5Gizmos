from H5Gizmos import Html, serve, do, get

async def task():
    greeting = Html("<h1>Hello</h1>")
    await greeting.show()

    # Get some values:
    innerHeight = await get(greeting.window.innerHeight)
    print ("The inner height is", innerHeight)
    height = await get(greeting.element.height())
    print ("The element height is", height)

    # Do some actions
    do(greeting.window.console.log("testing testing", [1, 2, 3]))
    do(greeting.element.text("Goodbye!"))

serve(task())
