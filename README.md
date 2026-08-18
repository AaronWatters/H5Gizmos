<img src="https://github.com/AaronWatters/H5Gizmos/raw/main/todo.gif" width="50%">

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/AaronWatters/H5Gizmos/HEAD)

# H5Gizmos

H5Gizmos presents an interactive graphical user interface for a Python program
in a web browser using HTML5 and Javascript.  The interactive interface 

- Can use arbitrary Javascript libraries.
- Can run as a stand alone application.
- Can run embedded in a Jupyter notebook in the notebook page.
- Can launch from a Jupyter notebook in a separate frame or window.
- Can display on the same computer as the Python program.
- Can display on a host that is remote from the host running the Python program.

The "parent" Python program launches a "child" Javascript context in a web browser.
The parent and child processes communicate using a web socket connection and HTTP protocols.

The animation below shows a gizmo script displaying a matplotlib plot running from the VS code editor.
The gizmo user interface appears as a new HTML frame in the browser instance below the editor.
Parameters for the plot are controlled by HTML form elements interactively.

<img src="https://github.com/AaronWatters/H5Gizmos/raw/main/doc/curves.gif" width="50%">

<a href="https://github.com/AaronWatters/H5Gizmos/blob/main/doc/curves.gif">[Link to image]</a>

Please see
<a href="https://github.com/AaronWatters/H5Gizmos/blob/main/doc/Tutorials/hello_curves.md">
the "hello curves" tutorial</a> for a detailed discussion of this
gizmo.

# Documentation

The documentation for H5Gizmos starts at

<a href="https://github.com/AaronWatters/H5Gizmos/blob/main/doc/README.md">doc/README.md.</a>

The H5Gizmos documentation is provided using Github markdown for simplicity.
If you wish to view the documentation locally from a clone of the repository,
please use
<a href="https://github.com/joeyespo/grip">https://github.com/joeyespo/grip</a>
or a similar github emulator.

# Installation

```bash
pip install H5Gizmos
```

# Development (or experimental) install

To install an experimental version of H5Gizmos, first clone or download
the H5Gizmos Github repository and then install in developer mode as follows:

```bash
 cd H5Gizmos
 pip install -e .
```
