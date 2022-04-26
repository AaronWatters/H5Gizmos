
from H5Gizmos import Html, serve
import numpy as np
import matplotlib.pyplot as plt

T = np.arange(100)
D = T * 0.2
X = D * np.sin(D)
Y = D * np.cos(D)

async def task():
    greeting = Html("<h1>A spiral</h1>")
    await greeting.show()
    plot = greeting.add_pyplot()
    with plot:
        plt.plot(X, Y)

serve(task())
