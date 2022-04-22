

# Gizmo dynamic interactions

This document describes methods for interacting with Gizmo components
after they have started.  The dynamic interactions can be divided into
those that change the parameters of a specific component and those that
change the interface more generally.

# Changing Component Parameters

Some component methods change the way a component responds to events
or how the component,

## Miscellaneous Document Object and jQuery Methods

```Python
from H5Gizmos import Html, serve, schedule_task, get, do, Button

async def task():
    image = Html('<img src="local_files/dog.png" width="200" height="200"/>')
    image.serve_folder("local_files", "./example_folder")
    await image.show()
    info = image.add("Put image info here.")

    async def show_image_info_task():
        element = image.element
        src = await get(element.attr("src"))
        info.text("src =" + repr(src))

    def show_cat(*args):
        do(image.element.attr("src", "local_files/cat.jpg"))
        schedule_task(show_image_info_task())

    image.add(Button("Show cat", on_click=show_cat))

    def show_dog(*args):
        do(image.element.attr("src", "local_files/dog.png"))
        schedule_task(show_image_info_task())

    image.add(Button("Show dog", on_click=show_dog))

    schedule_task(show_image_info_task())

serve(task())

```

<img src="dog_or_cat.gif"/>

<img src="clientHeight.png"/>

```Python
await get(image.element[0].parentElement.clientHeight)
```

# Parameter conveniences

## `component.text`

## `component.html`

## `component.empty`

## `component.on` and `component.off`

## `component.focus`

# Other Dynamic interactions

Some component methods change the interface by
enabling a feature or adding a new element to the interface.

## `component.enable_tooltip`

## `component.add_dialog`, `component.close_dialog`, `component.open_dialog`

## `component.add`

## `component.add_pyplot`

## `component.get_info_div`

## `component.shutdown_on_unload`

<a href="./README.md">
Return to introduction to running a Gizmo.
</a>