FROM python:3.8-slim-buster

WORKDIR /src

COPY . .

RUN pip install -e ./some_gizmo_demos

# The following command produces buffered output.
#CMD [ "gizmo_link", "9898", "/", "GizmoLink" ]

# Use unbuffered python
CMD [ "python", "-u", "start_server.py", "9898", "/", "GizmoLink" ]

# To run this docker build:
#docker build --tag gizmo-server .
#docker run --publish 5656:9898 gizmo-server
# Then open http://localhost:5656 in a browser.

