
# Javascript Interface and Data Transfers

This document discusses communication between the Python parent process and the Javascript child
process and introduces some special methods for large data transfers.

# Sending commands from parent to child

In gizmo programs the parent process sends commands to the child process.

```Python
from H5Gizmos import Html, serve, do, get

async def task():
    greeting = Html("<h1>Hello</h1>")
    await greeting.show()

    # Get some values:
    innerHeight = await get(greeting.window.innerHeight)
    print ("The inner height is", innerHeight)
    height = await get(greeting.element.height())
    print ("The element height is", height)

    # Do some actions
    do(greeting.window.console.log("testing testing", [1, 2, 3]))
    do(greeting.element.text("Goodbye!"))

serve(task())
```

Command line output...

```
(base) C02XD1KGJGH8:Javascript awatters$ python do_get_gizmo.py 
The inner height is 1480
The element height is 39
```

Javascript console...

<img src="console.png"/>

Interface display...

<img src="do_get.png">

## Javascript Reference Objects

### `component.element`

### `component.window`

### `component.document`

### `componeent.jQuery`

### Reference expressions

## `H5Gizmos.do`

## `H5Gizmos.get`

## Argument conversion

## Calling back to the parent

## `to_depth`

## `timeout`

# Declaring Dynamic Javascript

## `component.js_init`

## `component.function`

## `component.new`

# Caching Javascript Values

## `component.cache`

## `component.my`

## `component.uncache`

# Transferring binary data and large data

## `component.store_json`

## `component.store_array`

## `component.get_array_from_buffer`

## `component.translate_1d_array`

<a href="../README.md">
Return to H5Gizmos documentation root.
</a>
