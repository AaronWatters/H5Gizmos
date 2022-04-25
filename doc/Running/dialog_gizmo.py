
from H5Gizmos import Html, serve, do, Button

async def task():
    greeting = Html("""
    <div>
        <h2>For Your Eyes Only</h2>
        <h3>Sheena Easton</h3>
        <p>
            For your eyes only, can see me through the night <br>
            For your eyes only, I never need to hide <br>
            You can see so much in me, so much in me that's new <br>
            I never felt until I looked at you...
        </p>
    </div>
    """)
    await greeting.show()
    warning = Html("""
    <div>
        This page contains eyes-only sensitive information.<br>
        Hit [Enter] to close this dialog.
    </div>""")
    options = dict(resizeable=False, height="auto", width=200, modal=True)
    dialog = greeting.add_dialog(warning, dialog_options=options)
    dialog.focus()

    def close_on_enter(event):
        if event["keyCode"] == 13:  # enter key
            dialog.close_dialog()

    do(dialog.element.keypress(close_on_enter), to_depth=1)

    def reopen(*ignored):
        dialog.open_dialog()
        dialog.focus()

    greeting.add(Button("Show warning", on_click=reopen))

serve(task())
