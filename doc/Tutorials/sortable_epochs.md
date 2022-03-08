

# Tutorial `sortable_epochs.py`

The `sortable_epochs.py` script asks the user to drag geological epochs into the correct
time order.  It illustrates how to use ad-hoc Javascript in a Gizmo implementation and
how to get a value from the Javascript child process transferred to the parent process.

## The code

```Python
# sortable_epochs.py

from H5Gizmos import Html, Stack, Text, Button, do, get, serve, schedule_task

epoch_order = "archaen proterozoic paleozoic mesozoic tertiary pleistocene holocene".split()
bogus_order = "paleozoic holocene archaen proterozoic pleistocene tertiary mesozoic".split()

epochs = {name: Text(name) for name in epoch_order}
children = [epochs[name] for name in bogus_order]

sorter = Stack(children)
sorter.resize(width=400)
sorter.css(padding="10px")
info = Text("Drag the epochs to order them oldest (higher) to youngest (lower).")

async def task():
    Header = Html("<h3>Geological epochs</h3>")
    await Header.show()
    Header.add(sorter)
    do(sorter.element.sortable())
    sorter.js_init("""
        element.child_order = function () {
            var children = Array.from(element[0].children)
            result = children.map(x => x.textContent);
            return result;
        };
        """)
    def check_click(*ignored):
        schedule_task(check_task())
    Header.add(Button("check order", on_click=check_click))
    Header.add(info)

async def check_task():
    info.html("Please drag cyan elements earlier (higher) and magenta elements later (lower).")
    order = await get(sorter.element.child_order())
    correct = True
    for (index, epoch_name) in enumerate(order):
        correct_index = epoch_order.index(epoch_name)
        color = "yellow"
        if correct_index < index:
            color = "cyan"
            correct = False
        if correct_index > index:
            color = "magenta"
            correct = False
        epochs[epoch_name].css({"background-color": color})
    if correct:
        info.html("All correct!")

serve(task())
```

## The interface

Run like so:

```bash
% python sortable_epochs.py
```

The script opens a new tab in a browser that looks like this.

<img src="epochs.png">


## Discussion

This script mimicks <a href="hello2.md">hello2</a> by creating a header component as the primary component
in the initial `task` coroutine
and then attaching a number of other components using the `add` method.
The `task` adds a `sorter` `Stack` component which lists some geological epochs
in an incorrect time order.  The user is asked to put the epochs in the correct order
from oldest to youngest, and is provided with a `check` button which validates the correct
answer or gives hints for an incorrect answer.

### Executing Javascript methods using `do`

Most gizmo components in the gizmo parent process are associated with a `jQuery` container
object in the child Javascript context.  In the function call
```Python
    do(sorter.element.sortable())
```
`sorter.element` refers to the `jQuery` element associated with the `sorter` `Stack` object.
The expression `sorter.element.sortable()` refers to an unexecuted method call `sortable()` to be applied
to that `jQuery` object reference, and the `do(...)` function call sends the method call to the child
context to be executed.

When the child receives the message corresponding to the
```Python
    do(sorter.element.sortable())
```
execution request the child context locates the object `x` associated with `sorter.element`
and attempts to execute `x.sortable()`.  In this case the execution succeeds and
jQueryUI makes the `sorter` DOM object
<a href="https://jqueryui.com/sortable/">sortable</a> -- allowing the user
to drag the members of the list to different positions.

For completeness, note that a bad request like
```Python
    do(sorter.element.NO_SUCH_METHOD_EXISTS())
```
would fail to execute in the child and the child process would send an error message back to the parent asynchronously.

### Injecting Javascript code text using `js_init`

In order to check whether the user has arranged the epochs correctly
the script needs to get the currently displayed order for the epoch list.
The following `js_init` method call injects a small amount of Javascript
into the child context to get the epoch order:
```Python
    sorter.js_init("""
        element.child_order = function () {
            var children = Array.from(element[0].children)
            result = children.map(x => x.textContent);
            return result;
        };
        """)
```
The string argument to `js_init` contains the Javascript code text to inject.
```Javascript
        element.child_order = function () {
            var children = Array.from(element[0].children)
            result = children.map(x => x.textContent);
            return result;
        };
```
The reference `element` in the Javascript text refers to the `jQuery` element
associated with the `sorter` component.  The Javascript code fragment attaches
the `element.child_order` function to the `element` where `element.child_order()`
evaluates to the currenttly displayed sequence of epoch names.

### Getting Javascript values in the parent using `get`

The `check_order` coroutine uses the `get` method to execute `child_order`
in the child context and transfer the list of epochs to the parent as follows:
```Python
    order = await get(sorter.element.child_order())
```
The `get` sends a message requesting the return value of the `element.child_order()` function evaluated
in the Javascript child context and waits for the value to be transfered back to the parent.

Note that a `get` cannot be awaited directly in the button click callback `check_click`
because `check_click` is not a coroutine.  For this reason `check_click` launches the
`check_task()` coroutine which can `await get(...)`:
```Python
def check_click(*ignored):
    schedule_task(check_task())

async def check_task():
    ...
    order = await get(sorter.element.child_order())
    ...
```

<a href="README.md">Return to tutorial list.</a>
