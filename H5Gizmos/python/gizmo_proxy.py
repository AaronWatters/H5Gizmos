"""
Proxy server for publishing Gizmos over a specified connection port.

Basic functionality:
====================

The Proxy server starts using a PPORT which is reachable from the outside world.
When a Gizmo starts it selects a random GPORT which is usually only reachable in the local host
and awaits connections on the GPORT.

When the Proxy gets a request of form 

http://HOST:PPORT/gizmo_proxy/GPORT/SOME_PATH

the Proxy forwards the request to the internal Gizmo server using the connection

http://localhost:GPORT/gizmo/SOME_PATH

And the gizmo listening on GPORT handles the request.

Jupyter Server Proxy Notebook Use Case:
==============================

The following describes how a Jupyter server running remotely using Docker
or JupyterHub can forward connections to Gizmos using a Proxy as a jupyter_server_proxy.

When the Jupyter server starts it listens securely to a JPORT which is reachable from the outside world
serving connections of this form:

  https://JUPYTER_SERVER:JPORT/PATH

Server relative paths from the Jupyter interface in the user browser
of form "/PATH" will expand to connections of that form.
We need to use relative paths to access Gizmos because the JUPYTER_SERVER and JPORT
seen by the browser cannot be determined in order to submit a full path,
among other possible issues.

The Jupyter server starts a Proxy and provides it with a PPORT.  The
Proxy awaits connections of form:

    http://localhost:PPORT/...

The Proxy allows server relative URLs to connect to Gizmos as follows:

when a Gizmo starts in a notebook it allocates a random GPORT and awaits connections of form:

   http://localhost:GPORT/gizmo/SOME_PATH

The gizmo advertises a server relative connection URL in the Jupyter user interface of form:

    /gizmo_proxy/connect/GPORT/SOME_PATH

When the browser accesses the advertised URL within the Jupyter interface the URL expands to

    https://JUPYTER_SERVER:JPORT/gizmo_proxy/connect/GPORT/SOME_PATH

When the Jupyter server handles that request it forwards the request to the proxy port

    http://localhost:PPORT/gizmo_proxy/connect/GPORT/SOME_PATH

The Proxy forwards the above request to

    http://localhost:GPORT/gizmo/SOME_PATH

The gizmo that advertised the link then handles the request
and any requests with similar relative URLs derived from the request.

Jupyter Shell Command Line Use Case
===================================

A command line gizmo program starts in a shell interface and prints a connection link with a random GPORT like

    http://localhost:GPORT/gizmo/SOME_PATH"

The user pastes this link into the proxy HTML form on the main proxy page at

    https://JUPYTER_SERVER:JPORT/gizmo_proxy/

The form submit triggers the URL

    https://JUPYTER_SERVER:JPORT/gizmo_proxy/redirect?url=http://localhost:GPORT/gizmo/SOME_PATH"

The handler for `redirect` issues a server relative redirect to

    /gizmo_proxy/connect/GPORT/SOME_PATH

This forwards to the command line gizmo as described above.

Entry Points
============

Main Page "gizmo_proxy/": 
    General information and "Proxy and Url" form.

Proxy connect: "gizmo_proxy/connect/GPORT/SOME_PATH"
    Proxy GET, POST, and web socket connections to internal ports "http://localhost:GPORT/gizmo/SOME_PATH"

Redirect: "gizmo_proxy/redirect?url=http://localhost:GPORT/gizmo/SOME_PATH"
    Redirect the connection to "/gizmo_proxy/connect/GPORT/SOME_PATH"
"""

# References:

# Jupyter server proxy
# https://jupyter-server-proxy.readthedocs.io/en/latest/index.html

# openrefine example proxy:
# https://github.com/innovationOUtside/nb_serverproxy_openrefine/

# shiny proxy example:
# https://github.com/ryanlovett/jupyter-shiny-proxy

# aiohttp server reference
# https://docs.aiohttp.org/en/stable/web_reference.html

# aiohttp client reference
# https://docs.aiohttp.org/en/stable/client_reference.html

# aiohttp client article
# https://www.twilio.com/blog/asynchronous-http-requests-in-python-with-aiohttp

# aiohttp async streaming
# https://docs.aiohttp.org/en/stable/streams.html

# async proxy server gist
# https://gist.github.com/hirokiky/47fd9806ae98cfaffe1d

# repo2docker for local deployment in a container
# https://repo2docker.readthedocs.io/en/latest/index.html
