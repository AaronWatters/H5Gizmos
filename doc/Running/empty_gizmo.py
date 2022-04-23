
from H5Gizmos import Html, Input, serve

async def task():
    greeting = Html("<h1>What is six times seven?</h1>")
    await greeting.show()
    answer = Input()
    greeting.add(answer)
    response = greeting.add("No answer entered.")
    nag = greeting.add("Please type your answer in the input box above.")

    def check(*ignored):
        entered = answer.value.strip()
        if entered:
            nag.empty()
            try:
                assert int(entered) == 6 * 7
            except Exception:
                response.text(repr(entered) + " is incorrect.")
            else:
                response.html("<h1>Right!</h1>")
        else:
            nag.html("<em>Pretty please enter your answer in the box above.</em>")

    answer.on_enter(check)

serve(task())
