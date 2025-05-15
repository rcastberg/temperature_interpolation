ARG PYTHON_BUILDER_IMAGE=debian:12-slim
ARG GOOGLE_DISTROLESS_BASE_IMAGE=gcr.io/distroless/python3

## -------------- layer to give access to newer python + its dependencies ------------- ##

# syntax=docker/dockerfile:1
FROM ${PYTHON_BUILDER_IMAGE} as build

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends --yes python3-venv gcc libpython3-dev && \
    python3 -m venv /venv && \
    /venv/bin/pip install --upgrade pip setuptools wheel


# Build the virtualenv as a separate step: Only re-execute this step when requirements.txt changes
# syntax=docker/dockerfile:1
FROM build AS build-venv
COPY requirements.txt /requirements.txt
RUN /venv/bin/pip install --disable-pip-version-check -r /requirements.txt

    # Remove pip, setuptools, wheel
RUN rm -rf /venv/lib/python3.11/site-packages/pip* \
    /venv/lib/python3.11/site-packages/setuptools* \
    /venv/lib/python3.10/site-packages/wheel* \
    /usr/local/bin/pip 

# syntax=docker/dockerfile:1
FROM ${GOOGLE_DISTROLESS_BASE_IMAGE}

COPY --from=build-venv /venv /venv
COPY . /app
WORKDIR /app

ENTRYPOINT ["/venv/bin/python3", "-m" , "flask", "--app", "interpolate", "run", "--host=0.0.0.0"]