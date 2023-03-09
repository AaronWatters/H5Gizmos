
# Running Gizmos in Containers

This section discusses how to run a Gizmo interface inside a container
within the docker platform (or similar platforms).

## Why containers?

Containers deploy applications and components in isolation, greatly simplifying
software system management in networked environments.
<a href="https://www.ibm.com/topics/containerization">Please see the Containerization
article by IBM for more informations about containers and their advantages.</a>

## Why H5Gizmos in containers

Just like other processes
it is often useful for processes running in containers to provide a graphical interface
to control the process or report on the process status.
The H5Gizmos methodology provides a particularly simple way to implement a user
interface for a containerized application, but a gizmo inside a container needs
a little information about the external network environment to work correctly.

## Running a Gizmo using a specified port and server name

When a gizmo launches under normal conditions the parent process chooses and an arbitrary
available port and tries to infer an appropriate server name, advertizing a connection link
that might look something like this:
```
http://localhost:61952/gizmo/http/MGR_1654722075274_2/index.html 
```
Without some sort of additional mechanism this strategy will not work inside a container
because the container does not have access to the full networking information and
external networks do not have access to arbitrary ports inside the container.

If the process environment specifies `GIZMO_USE_SERVER_ADDRESS`
and `GIZMO_USE_PORT` the H5Gizmos infrastructure will use an externally determined port and server name.
For example if we launch
<a href="./docker_example/wavesurfer_poem.py">./docker_example/wavesurfer_poem.py</a>
using the `bash` system shell command
```bash
GIZMO_USE_SERVER_ADDRESS=127.0.0.1 GIZMO_USE_PORT=5678 python wavesurfer_poem.py
```
Then the gizmo interface advertizes a link using the specified port and server name (if the port is available)
like this:
```
http://127.0.0.1:5678/gizmo/http/MGR_1678290644892_2/index.html
```
These environment variables can inform a gizmo inside a container how to communicate with the outside world as
explained below.

## Launching a single Gizmo inside a container

This section discusses the 
<a href="docker_example/wavesurfer_poem.py">
docker_example wavesurfer poem container build
</a>
which is a version of the
<a href="../Tutorials/wavesurfer_poem.md">wavesurfer poem</a> example
modified to be self contained.

To create a container that advertises a single H5Gizmo interface we build a container
with the required internal components as usual.  For example here is the logic from
<a href="./docker_example/Dockerfile">./docker_example/Dockerfile with comments removed
```Dockerfile
FROM python:3.8-slim-buster
WORKDIR /src
RUN pip install H5Gizmos
COPY . .
CMD [ "python", "wavesurfer_poem.py" ]
```
We build the image for this Dockerfile with a Docker command line in the usual way
```bash
% docker build --tag wavesurfer_poem .
```

### Getting the <em>wrong</em> link

Without the help of environment variables a container
created from the `wavesurfer_poem` image built above
will advertise a connection link that won't work:
```bash
% docker run --publish 5555:5555 wavesurfer_poem

Open gizmo using link (control-click / open link)

<a href="http://172.17.0.2:39503/gizmo/http/MGR_1678371922265_2/index.html" target="_blank">Click to open</a> <br> 
 GIZMO_LINK: http://172.17.0.2:39503/gizmo/http/MGR_1678371922265_2/index.html 
```

The docker run command exposes port `5555` inside the container to the matching external port 5555,
but the H5Gizmo infrastructure chose to use port `39503` in the container which is not reachable
from the outside world.  Furthermore, the H5Gizmos infrastructure inferred the server name `172.17.0.2`
from inside the container, which does not correspond to an interface known outside the container.
Consequently the URL
```
http://172.17.0.2:39503/gizmo/http/MGR_1678371922265_2/index.html 
```
is useless and won't work outside of the container.

### Forcing the <em>right</em> link

To make a container using the `wavesurfer_poem` image that will work, we need to use
environment variables to force the H5Gizmos interface to produce a meaningful connection URL, like this:
```bash
% docker run \
    --env GIZMO_USE_SERVER_ADDRESS='localhost' \
    --env GIZMO_USE_PORT='5555' \
    --publish 5555:5555 wavesurfer_poem

Open gizmo using link (control-click / open link)

<a href="http://localhost:5555/gizmo/http/MGR_1678372543795_2/index.html" target="_blank">Click to open</a> <br> 
 GIZMO_LINK: http://localhost:5555/gizmo/http/MGR_1678372543795_2/index.html 
```
This forces the Gizmo server to connect to the mapped port `5555` and to advertise the meaningful
server name `localhost` in order to produce a URL which will work outside of the container.
```
http://localhost:5555/gizmo/http/MGR_1678372543795_2/index.html 
```

## Launching a many Gizmos inside a container using `gizmo_link`

A container can create many H5Gizmo interfaces by using the 
<a href="./GizmoLink.md">Gizmo Link Proxy Server</a> in combination with
<a href="./Scripts.md">Gizmo script entry points</a>.



<a href="./README.md">
Return to Gizmo Scripts and the GizmoLink Proxy Server.
</a>
