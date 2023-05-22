
# An example of launching a Gizmo server in a docker container.

This folder contains a recipe for building a docker container that offers two gizmo script
entry points.

Please see
<a href="../Containers.md">../Containers.md</a> for a discussion
of the use of the GizmoLink server and Gizmo script entry points
to serve multiple Gizmo interfaces from within a Docker container.

The following lists the files and folders of the implementation with brief descriptions.

<a href="./Dockerfile">./Dockerfile</a>:
The docker build instructions for the container.

<a href="./start_server.py">./start_server.py</a>:
The start script for the server running in the container.

<a href="./some_gizmo_demos">./some_gizmo_demos</a>:
The package top level folder for the components of the server.

<a href="./some_gizmo_demos/setup.py">./some_gizmo_demos/setup.py</a>:
The set up script for the `some_gizmo_demos` module implementing the components of the server.
This file defines the Gizmo script entry points used by the server.

<a href="./some_gizmo_demos/some_gizmo_demos">./some_gizmo_demos/some_gizmo_demos</a>:
The `some_gizmo_demos` module folder implementing the components of the server.

<a href="./some_gizmo_demos/some_gizmo_demos/__init__.py">./some_gizmo_demos/some_gizmo_demos/__init__.py</a>:
Required `__init__.py` file which also provides a documentation string used by the server
in script discovery.

<a href="./some_gizmo_demos/some_gizmo_demos/simple_todo.py">./some_gizmo_demos/some_gizmo_demos/simple_todo.py</a>:
The implementation of the "to do list" Gizmo script entry point.

<a href="./some_gizmo_demos/some_gizmo_demos/simple_todo.css">./some_gizmo_demos/some_gizmo_demos/simple_todo.css</a>:
A CSS file resource used by the "to do list" Gizmo script.

<a href="./some_gizmo_demos/some_gizmo_demos/hello_curves.py">./some_gizmo_demos/some_gizmo_demos/hello_curves.py</a>:
The implementation of the curves diagram Gizmo script entry point.

<hr>
<a href="../Containers.md">
Return to ../Containers.md
</a>
