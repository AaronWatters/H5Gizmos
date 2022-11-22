<img src="https://github.com/AaronWatters/H5Gizmos/raw/main/doc/lorenz.gif" width="50%">

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/AaronWatters/H5Gizmos/HEAD)

# H5Gizmos

A computer dashboard is a graphical user interface that provides real-time feedback about the state of a system or process. It is typically used in scientific and engineering applications where it is important to monitor the status of complex systems.

The computer dashboard was first developed at Lawrence Livermore National Laboratory in the early 1990s. It was designed to provide immediate feedback about the performance of supercomputers, which were then used for simulations of nuclear weapons tests. The original dashboard included several hundred individual gauges that displayed various aspects of system performance.

Today, computer dashboards are used in a wide variety of applications, from monitoring web servers and databases to tracking the progress of scientific experiments. They have also been adapted for use in business settings, where they can provide information about sales figures, customer satisfaction levels, and other key metrics.

H5Gizmos provides
tools for building dashboards and other
interactive graphical interfaces for applications using browser technology and HTML5. 

A Gizmo "child" interface displays in a standard web browser such as Chrome and communicates
with a "parent" Python process using a web socket and other HTTP protocols.  H5Gizmos can load and
use arbitrary Javascript resources to provide sophisticated interactive graphical interfaces.

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
