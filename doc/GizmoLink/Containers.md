
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

## Launching many Gizmos inside a container using `gizmo_link`

A container can create many H5Gizmo interfaces by using the 
<a href="./GizmoLink.md">Gizmo Link Proxy Server</a> in combination with
<a href="./Scripts.md">Gizmo script entry points</a>.

For example the
<a href="./server_docker_example/README.md">`server_docker_example`</a> provides
a recipe for building a docker container that offers two gizmo script
entry points.
The example includes a Python package implementation which defines
a `some_gizmo_demos` module that include Gizmo script entry points, the build instructions
for a container that installs `some_gizmo_demos`, and a start script for starting the server.

### Serving modules with entry points

To implement a server that offers multiple Gizmo interfaces
include Python packages that define the interfaces as Gizmo script entry points.
The example installs `some_gizmo_demos` using the following `setup.py` script:
```Python
from setuptools import setup

setup(
    name="some_gizmo_demos",
    install_requires=["H5Gizmos"],
    package_data={
        "some_gizmo_demos": [
            '*.css'
            ],
        },
    entry_points={
        "H5Gizmos.scripts": [
            "simple_todo = some_gizmo_demos.simple_todo:main",
            "hello_curves = some_gizmo_demos.hello_curves:main",
            "hello_env = some_gizmo_demos.hello_env:main",
        ]
    },
)
```
This setup script defines two `H5Gizmos.scripts` entry points: a "todo list" Gizmo interface
and a Gizmo which presents an interactive curve diagram.  The script also ensures that a CSS
file required by the `simple_todo` entry point is packaged with the module as `package_data`.

The example includes the implementation of the `some_gizmo_demos` module in the folder
<a href="./server_docker_example/some_gizmo_demos/some_gizmo_demos">./some_gizmo_demos/some_gizmo_demos</a>.

In general a server implementation will serve any number of modules that
define Gizmo script entry points.

### The startup script

The 
<a href="./server_docker_example/start_server.py">./start_server.py</a> script provides
minimal logic for starting a GizmoLink server
```Python
#!/usr/bin/env python -u

from H5Gizmos.python.gizmo_link import start_script
start_script()
```
The server will automatically detect and serve all Gizmo script entry points
defined in the Python installation, including the entry points defined by `some_gizmo_demos`.
The script is intended to be run by Python in unbuffered mode so that messages
from the server implementation are not delayed by buffering.

### Building the container

The example
<a href="./server_docker_example./Dockerfile">./Dockerfile</a>
describes how to build a container including the `some_gizmo_demos`
and how to start the GizmoLink server.  Here is the contents of the
Docker file with comments and whitespace removed:
```Dockerfile
FROM python:3.8-slim-buster
WORKDIR /src
COPY . .
RUN pip install -e ./some_gizmo_demos
CMD [ "python", "-u", "start_server.py", "9898", "/", "GizmoLink" ]
```
In brief these instructions 
- starts with an existing image which includes Python, 
- defines a working directory `src`,
- copies the example file structure to the working directory,
- installs the `./some_gizmo_demos` package from the local source, and
- uses the `start_server.py` script with unbuffered Python as a start command, which
starts the GizmoLink server on port 9898 inside the container.

### Building the container and starting the server

To launch the server in a container we must first build an image using the `docker build` command
```bash
cd server_docker_example
docker build --tag gizmo-server .
```
When we use the `gizmo-server` image name to launch a container the server will only be
reachable if we map the internal port `9898` used by the server to an external port
on the host where the container is running.  The following command maps the container
internal port `9898` to the host port `5656`.
```bash
docker run --publish 5656:9898 gizmo-server
```
The top level entry URL for the container is then available on the host as
```
 http://localhost:5656 
```
The responding page lists available Gizmo entry points.

### Direct script URLs

It is possible to use direct links to start a Gizmo interface in a containerized
server, but the link URL includes some redundancy.
For example the following URL starts an interface for the `hello_curves` entry
point in the `some_gizmo_demos` package for the server running on port `5656` on the `localhost`.

```
http://localhost:5656/?server=localhost&port=5656&module=some_gizmo_demos&script=hello_curves
```

The URL specifies the `server` and `port` as URL encoded parameters because the
process running in the container
cannot infer the external server name or port from the incoming connection alone
after the server and port have been mapped into the container.

Specifically the components of the connection URL break down as follows:

- `http://localhost:5656/` -- The host name `localhost` and host port `5656` for the server.
- `?server=localhost` -- the host name `localhost` repeated as a URL parameter.
- `&port=5656` -- the port `5656` repeated as a URL parameter.
- `&module=some_gizmo_demos` -- The module name `some_gizmo_demos` for the entry point.
- `&script=hello_curves` -- The entry point name (in that module) `some_gizmo_demos:hello_curves`.

URLs to directly connect to other entry points may be constructed in a similar manner.

<a href="./README.md">
Return to Gizmo Scripts and the GizmoLink Proxy Server.
</a>
