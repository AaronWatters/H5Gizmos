"""
Interactive 3d view of a Lorenz attractor system with
adjustable parameters.
"""

# Adapted from
# https://matplotlib.org/3.1.0/gallery/mplot3d/lorenz_attractor.html

import numpy as np
from H5Gizmos import Stack, Slider, Plotter, Text, serve, do
import matplotlib.pyplot as plt
# This import registers the 3D projection, but is otherwise unused.
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 unused import

def lorenz(x, y, z, s=10, r=28, b=2.667):
    '''
    Given:
       x, y, z: a point of interest in three dimensional space
       s, r, b: parameters defining the lorenz attractor
    Returns:
       x_dot, y_dot, z_dot: values of the lorenz attractor's partial
           derivatives at the point x, y, z
    '''
    x_dot = s*(y - x)
    y_dot = r*x - y - x*z
    z_dot = x*y - b*z
    return x_dot, y_dot, z_dot

plot_region = Plotter()

def draw_plot(*ignored):
    with plot_region:
        plot_curve()

info = Text("A parametric curve.")
s_text = Text("s")
s_slider = Slider(title="s", minimum=0.5, maximum=20, step=0.1, value=10, on_change=draw_plot)
r_text = Text("r")
r_slider = Slider(title="r", minimum=0.5, maximum=45, step=0.2, value=28,  on_change=draw_plot)
b_text = Text("b")
b_slider = Slider(title="b", minimum=0.5, maximum=4.5, step=0.02, value=2.6, on_change=draw_plot)
count = 0

dt = 0.01
num_steps = 10000

def plot_curve():
    # adapted from
    # https://www.geeksforgeeks.org/how-to-plot-a-smooth-curve-in-matplotlib/
    global count
    count += 1
    info.text("Draw # " + repr(count))
    b = b_slider.value
    s = s_slider.value
    r = r_slider.value
    b_text.text("b=" + repr(b))
    r_text.text("r=" + repr(r))
    s_text.text("s=" + repr(s))

    xs = np.empty(num_steps + 1)
    ys = np.empty(num_steps + 1)
    zs = np.empty(num_steps + 1)

    # Set initial values
    xs[0], ys[0], zs[0] = (0., 1., 1.05)

    # Step through "time", calculating the partial derivatives at the current point
    # and using them to estimate the next point
    for i in range(num_steps):
        x_dot, y_dot, z_dot = lorenz(xs[i], ys[i], zs[i], s, r, b)
        xs[i + 1] = xs[i] + (x_dot * dt)
        ys[i + 1] = ys[i] + (y_dot * dt)
        zs[i + 1] = zs[i] + (z_dot * dt)

    # Plot
    fig = plt.figure()
    #ax = fig.gca(projection='3d')
    ax = fig.add_subplot(projection='3d')

    ax.plot(xs, ys, zs, lw=0.5)
    ax.set_xlabel("X Axis")
    ax.set_ylabel("Y Axis")
    ax.set_zlabel("Z Axis")
    ax.set_title("Lorenz Attractor")
    #plt.show()

async def task():
    dashboard = Stack([
        s_text,
        s_slider,
        r_text,
        r_slider,
        b_text,
        b_slider,
        plot_region,
        info,
        ],
        child_css=dict(padding="5px"))
    dashboard.resize(width=600)
    await dashboard.show(verbose=True)
    draw_plot()

def main():
    """
    Interactive 3d view of a Lorenz attractor system with
    adjustable parameters.
    """
    serve(task(), verbose=True)

if __name__ == "__main__":
    main()
