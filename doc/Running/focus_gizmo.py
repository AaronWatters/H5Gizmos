
from H5Gizmos import serve, LabelledInput, Html

input = LabelledInput("Type stuff here: ")

def on_text(*ignored):
    txt = input.value
    input.label_container.add(Html("<p><em>%s</em></p>" % txt))
    input.set_value("")
    input.focus()

async def task():
    await input.label_container.show()
    input.on_enter(on_text)
    input.focus()

serve(task())
