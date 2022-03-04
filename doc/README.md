
# H5Gizmos documentation

This is the start page for H5Gizmo documentation.
The H5Gizmos documentation is provided using Github markdown for simplicity.
If you wish to view the documentation locally from a clone of the repository,
please use
<a href="https://github.com/joeyespo/grip">https://github.com/joeyespo/grip</a>
or a similar github emulator.

# Quickstart

The following silly example allows the user to select their favorite Beatle(s)
using a check box group.

```Python
from H5Gizmos import serve, CheckBoxes

async def task():

    def checked(values):
        print ("You chose", values)

    beatles = "John Paul George Ringo".split()
    G = CheckBoxes(beatles, legend="your favorite", on_click=checked)

    await G.show()

serve(task())
```
The following animation shows this script running from a VS code editor interface.
The Gizmo interface appears as a new tab in the browser below the editor.

<img src="demo2.gif">

This simple example illustrates some basic features of H5Gizmo interfaces.

- The interface is controlled and created by a Python "parent" process which
connects to a "child" Javascript web context in an HTML browser.

- The "parent" component runs in an asynchronous 
Python context like an `async` coroutine or a Jupyter code cell.
In this case the interface is created in the `task` coroutine.

- The interface is mediated by a controlling primary element which represents a link
between an HTML document object model (DOM) element in the child and the parent process.
In this case `G` refers to a Python object which corresponds to a checkbox group
in the browser.

- The Gizmo interface can make use of Javascript libraries.  In this case
the `Checkboxes` implementation automatically loads and uses the
<a href="https://jqueryui.com/">jQueryUI</a> library to implement the
check box group and its styling.

- The child Javascript context can call back to the parent in response to an event.
In this case when the user clicks the checkboxes the child calls back to the `checked`
Python function.  The parent process can also call-in to the child and optionally
wait for a return value, but this feature is not illustrated in this example and
is explained elsewhere.