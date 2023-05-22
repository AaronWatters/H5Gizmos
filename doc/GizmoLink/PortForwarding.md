
# Accessing a remote H5Gizmos interface using port forwarding

In some computational environments your computer may not
have a direct connection to a remote computing environment.
In such cases you can use secure shell port forwarding together
with the gizmo-link server to connect to an H5Gizmos user interfaces.

# On the remote host start a gizmo-link server on an available remote port (9876)

```bash
Worker3043$ gizmo_link 9876 / GizmoLink &
```

# On the remote host set the prefix environment variable for a mapped local port (16000)

```bash
Worker3043$ export GIZMO_LINK_PREFIX=http://127.0.0.1:16000/
```

# On the local workstation start an ssh port forwarding from the local to the remote port

```bash
local$ ssh -p 61022 -L 127.0.0.1:16000:Worker3043:9876 awatters@gateway.flatironinstitute.org
```

# On the remote host start the gizmo interface(s) using the prefix environment variable

```bash
Worker3043$ cd ~/repos/H5Gizmos/doc/
Worker3043$ python demo.py

Open gizmo using link (control-click / open link)

<a href="http://127.0.0.1:16000/connect/45385/gizmo/http/MGR_1684773058084_2/index.html" target="_blank">Click to open</a> <br> 
 GIZMO_LINK: http://127.0.0.1:16000/connect/45385/gizmo/http/MGR_1684773058084_2/index.html 


```

# Open the URL for the interfaces on the local workstation

```bash
local$ open http://127.0.0.1:16000/connect/45385/gizmo/http/MGR_1684773058084_2/index.html
```

<a href="./README.md">
Return to Gizmo Scripts and the GizmoLink Proxy Server.
</a>
