
# Gizmo configuratinn

This document describes resource specifications and other configurations
which either must or may be specified before the primary component
is started.

# Static only configurations

The following configurations must be specified before the main component starts.

## `component.serve_folder`

The `serve_folder` directive configures the Gizmo HTTP server
to recursively serve the files in a folder on the machine running
the parent process.  In the example below the HTTP server serves
the contents of `./example_folder` identified with the URL prefix
`local_files`.

```Python
from H5Gizmos import Html, serve

async def task():
    greeting = Html("<h1>Hello</h1>")
    greeting.serve_folder("local_files", "./example_folder")
    await greeting.show()
    greeting.add(Html('<img src="local_files/dog.png"/>'))

serve(task())
```

The added HTML
```Python
    greeting.add(Html('<img src="local_files/dog.png"/>'))
```
refers to the server relative file `"local_files/dog.png"`
which the server maps to the path `"./example_folder/dog.png"`
in the file system.  The server attempts to assign an appropriate
MIME type to the served file (in this case correctly guessing "img/png").

The gizmo presents the following page including the mapped image:

<img src="dog_gizmo.png" width="300">

Served folders are useful for loading related files from complex
Javascript functionality which may combine Javascript modules,
CSS styles, images, and other sorts of data files.

## `component.set_icon`

By default a stand alone gizmo presents a standard icon
in the browser frame list bar.

<img src="../../H5Gizmos/static/icon.png">

A script may change the icon using the `set_icon` method.
The script below changes the icon to use the `dog.png` image
shown above.

```Python
from H5Gizmos import Html, serve

async def task():
    greeting = Html("<h1>Hello</h1>")
    greeting.set_icon("./example_folder/dog.png")
    await greeting.show()

serve(task())
```

A run of 
```bash
% python dog_icon.py
```
Displays a small icon with the dog image above the
browser frame

<img src="dog_icon.png" width="500"/>

It is also useful to "view source" on the browser frame
to see the icon listed in the static HTML source.
In this case the following line in the listing
specifies the icon:

```html
<link rel="icon" type="image/png" href="./icon.png"/>
```

Clicking on the icon URL in the Chrome browser
source display will show the full size image.

Viewing source can be useful for other static
configurations described here as well.

## `component.remote_css`

The Gizmo infrastructure provides several methods for
loading CSS style sheets statically before the main component
starts.

The `remote_css` method loads a CSS stylesheet from a remote
web server using a fully specified URL.

For example the CSS style at this remote URL includes fancy
styling for buttons
```
https://aaronwatters.github.io/visualization_prototypes/css/base.css
```
The following script uses this style sheet to style a button
```Python
from H5Gizmos import Button, serve

async def task():
    button = Button("Click Me")
    def on_click(*ignored):
        button.add("Hi there! Thanks!")
    button.set_on_click(on_click)
    button.remote_css(
        "https://aaronwatters.github.io/visualization_prototypes/css/base.css"
    )
    await button.show()

serve(task())
```
The resulting gizmo interface shows button text
in all capital letters using a fancy font:

<img src="remote_css.png">


## `component.css_file`

The `css_file` method loads a CSS stylesheet from a file in
the filesystem accessible to the parent process.

The script below loads the CSS stylesheet at the path
`"./css_file_example.css"` before the main component starts.

```Python
from H5Gizmos import Html, serve

async def task():
    greeting = Html("""
    <div>
    <h1>This header should be green</h1>
    But this plain text should be blue.
    </div>
    """)
    greeting.css_file("./css_file_example.css")
    await greeting.show()

serve(task())
```

The content of `"./css_file_example.css"`specifies
colors for text as follows:

```CSS
body {
    color: blue;
}

h1 {
    color: green;
}
```

The stylized gizmo interface looks like this:

<img src="css_file.png"/>

## `component.relative_css`

```Python
from H5Gizmos import Html, serve

async def task():
    greeting = Html("""
    <div>
    <h1>This header should be red</h1>
    But this plain text should be orange.
    </div>
    """)
    greeting.serve_folder("local_files", "./example_folder")
    greeting.relative_css("./local_files/relative_css_example.css")
    await greeting.show()

serve(task())
```

```CSS
body {
    color: orange;
}

h1 {
    color: red;
}
```

<img src="relative_css.png">

## `component.embedded_css`

```Python
from H5Gizmos import Html, serve

async def task():
    greeting = Html("""
    <div>
    <h1>This header should be brown</h1>
    But this plain text should be salmon.
    </div>
    """)
    greeting.embedded_css("""
        body {
            color: salmon;
        }
        h1 {
            color: brown;
        }
    """)
    await greeting.show()

serve(task())
```

<img src="embedded_css.png">

## `component.insert_html`

```Python
from H5Gizmos import Html, serve
import time
import asyncio

async def task():
    the_time = Html("<h1>Time here</h1>")
    the_time.insert_html("""
    <h3>A timer.</h3>
    <p>
    The following header will show the current
    time for 60 seconds.
    </p>
    """)
    await the_time.show()
    for i in range(60):
        the_time.text("time is now: " + time.ctime())
        await asyncio.sleep(1)
    the_time.add("Finished!")

serve(task())
```

<img src="insert_html.png"/>

## `component.relative_js`

## `component.embedded_script`

## `component.remote_js`

## `component.js_file`

# Static and Dynamic configurations

The following configurations may be specified before or after the main component starts.

## `component.set_title`

## `component.resize`

## `component.addClass` and `component.removeClass`

## `component.css`

## `component.set_on_click`

## `component.on_timeout`

## `component.add_content`

<a href="./README.md">
Return to introduction to running a Gizmo.
</a>
