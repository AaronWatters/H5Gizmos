

# H5Gizmos Tutorials

This documentation subsection provides a number of tutorials
which walk through H5Gizmo implementations in order to illustrate
and explain features of the infrastructure.

The tutorials are roughly organized in order of increasing
conceptual complexity.

<h2>
<a href="hello1.md">
Hello 1
</a>
</h2>

The `hello1.py` script displays the current time and updates the display every second.
It demonstrates starting an H5Gizmo interface with two components and updating displayed text.


<h2>
<a href="hello2.md">
Hello 2
</a>
</h2>

The `hello2.py` is similar to "hello1" but updates the time display in response to a button click,
not automatically.


<h2>
<a href="hello3.md">
Hello 3
</a>
</h2>

The `hello3.py` is similar to "hello2" but the visual components are organized into
a grid using a composite `Stack` component, and some random styling is added.


<h2>
<a href="hello_curves.md">
Hello Curves
</a>
</h2>

The `hello_curves.py` script builds a `Stack` dashboard containing
input sliders which control parameters for a `matplotlib` curve visualization.

<h2>
<a href="sortable_epochs.md">
Sortable Epochs
</a>
</h2>

The `sortable_epochs.py` script asks the user to drag geological epochs into the correct
time order.  It illustrates how to use ad-hoc Javascript in a Gizmo implementation and
how to get a value from the Javascript child process transferred to the parent process.

<h2>
<a href="wavesurfer_poem.md">
Wavesurfer poem
</a>
</h2>

The `wavesurfer_poem.py` script controls an audio player implemented using
an external Javascript library.  It demonstrates how to load Javascript functionality
for a gizmo and how to attach external resources to a gizmo.

<h2>
<a href="simple_todo.md">
Simple to-do list
</a>
</h2>

The `simple_todo.py` script implements a simple "to do list" reminder dashboard.
It illustrates how to style a dashboard using the `Template` composite component
and external CSS style sheets.


<a href="../README.md">
Return to H5Gizmos documentation root.
</a>