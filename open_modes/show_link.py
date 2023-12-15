from H5Gizmos import serve, CheckBoxes

print("Offering link which the user can use to open the gizmo.")

async def task():

    def checked(values):
        print ("You chose", values)

    beatles = "John Paul George Ringo".split()
    G = CheckBoxes(beatles, legend="your favorite", on_click=checked)

    #await G.show()
    await G.link()

serve(task())
