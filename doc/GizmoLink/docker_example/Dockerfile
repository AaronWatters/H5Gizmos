FROM python:3.8-slim-buster

WORKDIR /src

# Install H5Gizmos
RUN pip install H5Gizmos

# Copy all files from the docker_example folder to /src in the container
COPY . .

# Run the gizmo
CMD [ "python", "wavesurfer_poem.py" ]

# To use this Dockerfile:
# $ docker build --tag wavesurfer_poem .
# $ docker run --env GIZMO_USE_SERVER_ADDRESS='localhost' --env GIZMO_USE_PORT='5555' --publish 5555:5555 wavesurfer_poem
