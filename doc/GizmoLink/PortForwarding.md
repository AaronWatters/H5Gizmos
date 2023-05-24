
# Accessing a remote H5Gizmos interface using port forwarding

In some computational environments your computer may not
have a direct connection to a remote computing environment.
In such cases you can use secure shell port forwarding together
with the gizmo-link server to connect to H5Gizmos user interfaces
running on remote machines.

For the sake of concreteness the following discussion illustrates
how to open H5Gizmo interfaces using port forwarding within the
Flatiron Institute (FI) environment at the time of this writing.
You may need to adjust details for your environment.

In the discussion below I have installed H5Gizmos on the FI compute cluster
and I want to view H5Gizmos user interfaces for programs running on the
cluster on my local workstation -- but my local workstation does not
have a direct network connection to the cluster.  The only network access
for my workstation to the cluster is via the secure shell mechanism `ssh`.

First we need to connect to a compute node to use run H5Gizmos programs
in the cluster.  A guest researcher at FI might use the `gateway`
to get access to the cluster by running a console command
on the local workstation like this: 

```bash
local$ ssh -p 61022 awatters@gateway.flatironinstitute.org
...
gateway$ 
```

Above `awatters@gateway.flatironinstitute.org` is my username -- you will need
to use your user name, of course.  The `-p 61022` flag specifies that the gateway
uses `61022` as the ssh connection port.  The `ssh` connection may require passwords
and other authentication.

From the gateway node the researcher would probably connect to one of
the cluster login nodes such as `rusty` like this:

```bash
gateway$ ssh rusty
```

To access a node that is appropriate for running non-trivial computations
the researcher might use `srun` to allocate a compute node, like this:
```
rusty$ srun -N1 --pty bash -i
worker$ uname -a
Linux worker6027 5.15.90.1.fi #1 SMP Thu Jan 26 14:11:06 EST 2023 x86_64 x86_64 x86_64 GNU/Linux
worker$
```
The allocated node `worker6027` is appropriate for general purpose computations.

The following discussion describes how the researcher can launch any number of H5Gizmos user interfaces
on `worker6027` and connect to the interfaces from a user facing "local workstation" (such as a laptop)
using port forwarding.  Below the node name `worker6027` is just an example name -- in general you will need
to use whatever "remote host" name that is allocated by `srun`.

### On the remote host start a gizmo-link server using an available remote port (9876)

The `gizmo_link` server provides a web server running on a specific port which
can connect to H5Gizmo user interfaces running on the remote host `worker6027`.  Start
the server on port 9876 on `worker6027` like this:
```bash
worker6027$ gizmo_link 9876 / GizmoLink &
```
It is possible you may need to
use some other port for the server if port 9876 is not available on the remote host.

The above line starts the server running in the background, because it ends with `&`.
You can launch other programs
from the same console by hitting "return" to get a new prompt.  

### On the local workstation establish forwarding to the remote port

Next, we set up port forwarding between the local workstation and the remote host
by running a command line in a console window on the local workstation.
The following console command 
sets up an `ssh` port forwarding tunnel which connects port 16000 on the
local workstation to port 9876 on the remote host `worker6027`.

```bash
local$ ssh -p 61022 -L 127.0.0.1:16000:Worker6027:9876 awatters@gateway.flatironinstitute.org
```

You will need to replace `worker6027` with the name allocated by `srun` above, and will need to
use your username, and it is possible you may need to change the port numbers if they are not
available.
The `ssh` connection may require passwords
and other authentication.

### On the local workstation open the gizmo-link test page

At this point you can verify that the port forwarding is working by opening the
gizmo-server test page in a browser.  On a Mac laptop this can be done from the
command line like this:

```bash
local$ open http://127.0.0.1:16000/test
```

If everything is working you should see a browser tab containing a "hello world"
page listing some information about the gizmo-server program.

### On the remote host start the gizmo interface(s) using a prefix environment variable

Now it is possible to launch H5Gizmos interfaces on the remote host and connect to them
from the local workstation.  But first define the following environment variable on the remote
console so the H5Gizmos infrastructure knows to construct URLs using the forwarded port:

```bash
Worker6027$ export GIZMO_LINK_PREFIX=http://127.0.0.1:16000/
```

Now when you start an H5Gizmos interface from the remote console it will print
a connection URL that uses the forwarded port, like this:

```bash
Worker6027$ cd ~/repos/H5Gizmos/doc/
Worker6027$ python demo.py

Open gizmo using link (control-click / open link)

<a href="http://127.0.0.1:16000/connect/45385/gizmo/http/MGR_1684773058084_2/index.html" target="_blank">Click to open</a> <br> 
 GIZMO_LINK: http://127.0.0.1:16000/connect/45385/gizmo/http/MGR_1684773058084_2/index.html 
```

### Open the URL for the interface(s) on the local workstation

The URL generated above by the H5Gizmos interface can be opened on the local workstation
in a browser.  On a Mac laptop this can be done from the command line like this:

```bash
local$ open http://127.0.0.1:16000/connect/45385/gizmo/http/MGR_1684773058084_2/index.html
```

Using the above environment variable binding, any number of H5Gizmos interfaces can use the
same forwarded port between the local workstation and the remote host.

<a href="./README.md">
Return to Gizmo Scripts and the GizmoLink Proxy Server.
</a>
