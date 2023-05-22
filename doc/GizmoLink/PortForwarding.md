
# Accessing a remote H5Gizmos interface using port forwarding

In some computational environments your computer may not
have a direct connection to a remote computing environment.
In such cases you can use secure shell port forwarding together
with the gizmo-link server to connect to an H5Gizmos user interfaces.

```bash
localhost$ ssh -p 61022 awatters@gateway.flatironinstitute.org
gateway$ ssh rusty
rusty$ srun -N1 --pty bash -i
worker$ uname -a
Linux worker6027 5.15.90.1.fi #1 SMP Thu Jan 26 14:11:06 EST 2023 x86_64 x86_64 x86_64 GNU/Linux
```

# On the remote host start a gizmo-link server using an available remote port (9876)

```bash
worker6027$ gizmo_link 9876 / GizmoLink &
```

# On the local workstation start an ssh port forwarding from the local to the remote port

```bash
localhost$ ssh -p 61022 -L 127.0.0.1:16000:Worker6027:9876 awatters@gateway.flatironinstitute.org
```

# On the localhost open the gizmo-link test page

```bash
localhost$ open http://127.0.0.1:16000/test
```

# On the remote host start the gizmo interface(s) using the prefix environment variable

```bash
Worker6027$ export GIZMO_LINK_PREFIX=http://127.0.0.1:16000/
```

```bash
Worker6027$ cd ~/repos/H5Gizmos/doc/
Worker6027$ python demo.py

Open gizmo using link (control-click / open link)

<a href="http://127.0.0.1:16000/connect/45385/gizmo/http/MGR_1684773058084_2/index.html" target="_blank">Click to open</a> <br> 
 GIZMO_LINK: http://127.0.0.1:16000/connect/45385/gizmo/http/MGR_1684773058084_2/index.html 
```

# Open the URL for the interface(s) on the local workstation

```bash
localhost$ open http://127.0.0.1:16000/connect/45385/gizmo/http/MGR_1684773058084_2/index.html
```

<a href="./README.md">
Return to Gizmo Scripts and the GizmoLink Proxy Server.
</a>
