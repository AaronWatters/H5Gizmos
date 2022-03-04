# H5Gizmos

H5Gizmos provides
tools for building interactive graphical interfaces for applications using browser technology and HTML5. Gizmo "child" interfaces run in standard web browsers such as Chrome and communicate
with a "parent" Python process using a web socket and other HTTP protocols.  H5Gizmos can load and
use arbitrary Javascript resources to provide complex and advanced interactive graphical interfaces.

The animation below shows a gizmo script displaying a matplotlib plot running from the VS code editor.
The gizmo user interface appears as a new HTML frame in the browseer instance below the editor.

<div style="background-color:green; padding:25;">
<img src="doc/curves.gif">
</div>

# Documentation

The documentation for H5Gizmo starts at

<a href="doc/README.md">doc/README.md.</a>

The H5Gizmos documentation is provided using Github markdown for simplicity.
If you wish to view the documentation locally from a clone of the repository,
please use
<a href="https://github.com/joeyespo/grip">https://github.com/joeyespo/grip</a>
or a similar github emulator.

# Development (or experimental) install

To install an experimental version of H5Gizmos, first clone or download
the H5Gizmos Github repository and then install in developer mode as follows:

```bash
 cd H5Gizmos
 pip install -e .
```
