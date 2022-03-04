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
    plt.title(r"$x = \sin(%s t), y = cos(%s t)$" % (a, b))
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
