

# Tutorial `hello_curves.py`

The `hello_curves.py` script builds a `Stack` dashboard containing
input sliders which control a parameters for a `matplotlib` curve visualization.

The plottting method used here can add visual elements to gizmos
using any technique based in
<a href="https://matplotlib.org/">matplotlib</a>
such as 
<a href="https://seaborn.pydata.org/">seaborn</a>.

## The code

```Python
# hello_curves.py

import numpy as np
from H5Gizmos import Stack, Slider, Plotter, Text, serve, do
import matplotlib.pyplot as plt

plot_region = Plotter()

def draw_plot(*ignored):
    with plot_region:
        plot_curve()

info = Text("A parametric curve.")
a_text = Text("a")
a_slider = Slider(title="a", minimum=0.5, maximum=4.5, step=0.02, on_change=draw_plot)
b_text = Text("b")
b_slider = Slider(title="b", minimum=0.5, maximum=4.5, step=0.02, on_change=draw_plot)
count = 0

def plot_curve():
    # adapted from
    # https://www.geeksforgeeks.org/how-to-plot-a-smooth-curve-in-matplotlib/
    global count
    count += 1
    info.text("Draw # " + repr(count))
    a = a_slider.value
    b = b_slider.value
    a_text.text("a = " + repr(a))
    b_text.text("b = " + repr(b))
    xs = []
    ys = []
    for i in range(300):
        t = i / 33.0
        x = np.sin( a * t )
        y = np.cos( b * t )
        xs.append(x)
        ys.append(y)
    plt.plot(xs, ys)
    plt.title(r"$x = \sin(%s t), y = \cos(%s t)$" % (a, b))
    plt.xlabel("X")
    plt.ylabel("Y")
    #plt.show()

async def task():
    dashboard = Stack([
        a_text,
        a_slider,
        b_text,
        b_slider,
        plot_region,
        info,
        ],
        child_css=dict(padding="5px"))
    dashboard.resize(width=600)
    await dashboard.show()
    draw_plot()

serve(task())
```

## The interface

Run like so:

```bash
% python hello_curves.py
```

The script opens a new tab in a browser.

The animation below shows the script started from the
VS code editor interface.  The dashboard interface appears
in a new browser tab in the browser running below the editor
window.

<img src="../curves.gif" width="50%">


## Discussion

This script mimicks <a href="hello3.md">hello3</a> by
creating a composite `Stack` `dashboard` and starting the
`dashboard` interface.

The `Stack` `dashboard` includes a `plot_region` `Plotter` area and two `Slider` controls
for displaying a `matplotlib` plot and adjusting the parameters for
the plot. The `draw_plot` function executes when the script initializes and when the sliders change.

After initialization the asynchronous event loop waits for changes to the sliders
or for a shut down event.

The `draw_plot` function uses the `plot_region` `Plotter` object as a `with`
context manager to capture the global `matplotlib` plot object as
an image and transfer the image to the child process.

```Python
def draw_plot(*ignored):
    with plot_region:
        plot_curve()
```

The `plot_curve` function draws a standard `matplotlib` plot
using the current values from the sliders as parameters.

```Python
import matplotlib.pyplot as plt
...

def plot_curve():
    ...
    a = a_slider.value
    b = b_slider.value
    ...
    plt.plot(xs, ys)
    ...
    #plt.show()
```
Note that `plt.show()` is commented because the `plot_region`
context manager does the work to show the plot.  The standard
`plt.show()` will not work here.


<a href="README.md">Return to tutorial list.</a>
