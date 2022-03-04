from sre_constants import CHCODES
from H5Gizmos import serve, CheckBoxes

async def task():

    def checked(values):
        print ("You chose", values)

    beatles = "John Paul George Ringo".split()
    G = CheckBoxes(beatles, legend="your favorite", on_click=checked)

    await G.browse()

serve(task())