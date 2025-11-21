# Dockerfile - small python image for UDP rendezvous + TCP relay
FROM python:3.11-slim


WORKDIR /app


# copy server
COPY server.py /app/server.py
RUN chmod +x /app/server.py


# expose default port (informational; actual port is read from PORT env)
EXPOSE 9999


CMD ["python", "/app/server.py"]