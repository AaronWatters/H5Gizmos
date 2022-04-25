
from H5Gizmos import Html, serve, LabelledInput

async def task():
    greeting = Html("<h1>Your information</h1>", title="Please tell us about yourself")
    await greeting.show()
    greeting.enable_tooltips()
    greeting.add(
        LabelledInput("Your name*: ", title="Required field")
        .label_container)
    greeting.add(Html("<br>"))
    greeting.add(
        LabelledInput("Your age:", title="Optional. We ask for you age only for statistical purposes.")
        .label_container)

serve(task())
