from H5Gizmos import serve, CheckBoxes

print("Attempting to open gizmo in browser automatically.")

async def task():

    def checked(values):
        print ("You chose", values)

    beatles = "John Paul George Ringo".split()
    G = CheckBoxes(beatles, legend="your favorite", on_click=checked)

    await G.show()
    #await G.link()

serve(task())
