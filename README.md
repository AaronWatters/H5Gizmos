<img src="https://github.com/AaronWatters/H5Gizmos/raw/main/doc/lorenz.gif" width="50%">

# H5Gizmos

H5Gizmos provides
tools for building interactive graphical interfaces for applications using browser technology and HTML5. 

A Gizmo "child" interfaces runs in a standard web browser such as Chrome and communicates
with a "parent" Python process using a web socket and other HTTP protocols.  H5Gizmos can load and
use arbitrary Javascript resources to provide sophisticated interactive graphical interfaces.

The H5Gizmo mechanism is designed to facilitate the development of "dashboards" and special purpose
tools for scientific and technical workflows.

The animation below shows a gizmo script displaying a matplotlib plot running from the VS code editor.
The gizmo user interface appears as a new HTML frame in the browser instance below the editor.

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
