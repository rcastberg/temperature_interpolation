# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /python-docker

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY interpolate.py .

CMD [ "python3", "-m" , "flask", "--app", "interpolate", "run", "--host=0.0.0.0"]
