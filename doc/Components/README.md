
# H5Gizmo Components 

This section describes standard components for building an H5Gizmos interface.

Components are basic building blocks for creating H5Gizmo interfaces -- a gizmo is connected to a primary
component which encapsulates the connection between the parent process and the child context.  Other components
may be attached to the primary component or contained within the primary component.

<h2>
<a href="Simple.md">
Simple components
</a>
</h2>

Simple components such as buttons and text do not contain other non-trivial components.

<h2>
<a href="Composite.md">
Composite Components
</a>
</h2>

Composite components such as `Template`s and `Stack`s build structures that include other components.

<h2>
<a href="Building.md">
Building Components
</a>
</h2>

You can build components to encapsulate additional functionality implemented in Javascript
by subclassing one of the Component implementations.



<a href="../README.md">
Return to H5Gizmos documentation root.
</a>
