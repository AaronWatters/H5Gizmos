
# Building Components

You can build components to encapsulate additional functionality implemented in Javascript
by subclassing one of the Component implementations.

New component implementations often load external Javascript libraries and create interfaces
to Javascript objects configured using the external libraries.
The new component may also provide additional special methods that allow the gizmo which
uses the component to interact with the Javascript functionality.

### `component.add_dependancies`

### `component.initial_reference`

### `component.configure_jQuery_element`

### `component.dom_element_reference`

## Some external examples

### `jp_doodle dual_canvas`

The `jp_doodle` repository includes an `H5Gizmo` wrapper implementation
<a href="https://github.com/AaronWatters/jp_doodle/blob/master/jp_doodle/gz_doodle.py">
https://github.com/AaronWatters/jp_doodle/blob/master/jp_doodle/gz_doodle.py
</a> which embeds a `dual_canvas` in a gizmo container for drawing geometric diagrams.

### `feedWeGL2` isosurface viewer

The `feedWebGL2` repository wraps a three dimensional isosurface viewer as an H5Gizmo component:
<a href="https://github.com/AaronWatters/feedWebGL2/blob/master/feedWebGL2/volume_gizmo.py">
https://github.com/AaronWatters/feedWebGL2/blob/master/feedWebGL2/volume_gizmo.py</a>.

<a href="./README.md">
Return to Component categories.
</a>
