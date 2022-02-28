import numpy as np
from H5Gizmos import Stack, Slider, Plotter, Html, serve
import matplotlib.pyplot as plt

plot_region = Plotter()

def draw_plot(*ignored):
    with plot_region:
        plot_curve()

a_slider = Slider(title="a", minimum=0.5, maximum=4.5, step=0.2, on_change=draw_plot)
b_slider = Slider(title="b", minimum=0.5, maximum=4.5, step=0.2, on_change=draw_plot)

def plot_curve():
    # adapted from
    # https://www.geeksforgeeks.org/how-to-plot-a-smooth-curve-in-matplotlib/
    a = a_slider.value
    b = b_slider.value
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
    dashboard = Stack([["a", a_slider], ["b", b_slider], plot_region])
    await dashboard.show()
    draw_plot()

serve(task())
