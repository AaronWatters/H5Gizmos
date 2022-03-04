

# Tutorial `hello2.py`

## The code

```Python
# hello3.py
from H5Gizmos import Html, Text, Button, Stack, serve
import asyncio, time

greeting = Html("<h1>Hello</h1>")
the_time = Text("No time like the present")
clicker = Button("Click me!")
count = 0

def click_callback(*ignored):
    global count
    count += 1
    greeting.html("<em>That tickles</em>")
    the_time.text("%s: the time is now %s" % (count, time.ctime()))

clicker = Button("Click me!", on_click=click_callback)

dashboard = Stack([
    greeting,
    [clicker, the_time]
])
dashboard.css({"justify-content": "center"})
greeting.css(color="salmon")
the_time.css(color="darkcyan")
clicker.css({"color": "darkred", "background-color": "pink"})

async def task():
    await dashboard.show()

serve(task())
```

## The interface

Run like so:

```bash
% python hello3.py
```

The script opens a new tab in a browser that looks like this.

<img src="hello3.png">

And the time value updates when the user clicks the "Click me" button.


## Discussion


<a href="README.md">Return to tutorial list.</a>
