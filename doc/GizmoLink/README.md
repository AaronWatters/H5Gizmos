
# Containers, Gizmo Scripts and the GizmoLink Proxy Server

This section discusses how to run Gizmo interfaces in internet cloud environments.
H5Gizmo interfaces running in containers can display on remote web browsers and 
the `GizmoLink` proxy server helps user web browsers
display Gizmo user interfaces where the parent process runs on a remote machine.
The section also describes how to declare Gizmo script entry points that can be
advertized and launched by the proxy server.

<h2>
<a href="PortForwarding.md">
Running Gizmos remotely using port forwarding
</a>
</h2>

In some computational environments your computer may not
have a direct connection to a remote computing environment.
In such cases you can use secure shell port forwarding together
with the gizmo-link server to connect to a H5Gizmos user interfaces.

<h2>
<a href="Containers.md">
Running Gizmos in Containers
</a>
</h2>

A process running in a Docker container can present an H5Gizmo user interface
if the container is configured to connect the gizmo server to the correct port
and to use the correct server name.

<h2>
<a href="GizmoLink.md">
The Gizmo Link Proxy Server
</a>
</h2>

The Gizmo Link Proxy Server connects "child" user interfaces to "parent" processes
running on remote machines.


<h2>
<a href="Scripts.md">
H5Gizmo script entry points
</a>
</h2>

H5Gizmo script entry points advertise Gizmo scripts designed to be launched
by the Gizmo Link proxy server.


<a href="../README.md">
Return to H5Gizmos documentation root.
</a>
