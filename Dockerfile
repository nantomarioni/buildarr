# Dockerfile
# Custom Buildarr Docker image with all plugins bundled as a monorepo.
# Based on buildarr v0.7.1 (pydantic v1) for full plugin compatibility.
FROM python:3.11-alpine

# Ensure stdout/stderr writes straight through to the Docker logs without buffering.
ENV PYTHONUNBUFFERED=1

# Buildarr user UID/GID. User is created at runtime.
ENV PUID=1000
ENV PGID=1000

# Mark the Buildarr configuration folder as an external volume mount point.
VOLUME ["/config"]

# Copy the entire monorepo source into the image.
COPY . /src

# Install system dependencies and the monorepo (core + all plugins) in one go.
RUN apk add --no-cache su-exec tzdata && \
    pip install --no-cache-dir /src

# Set the Buildarr configuration folder as the default working directory.
WORKDIR /config

# Create a simple entrypoint that handles user creation and exec.
RUN printf '#!/bin/sh\nset -eu\ndeluser buildarr 2>/dev/null || true\ndelgroup buildarr 2>/dev/null || true\naddgroup -S -g $PGID buildarr\nadduser -S -s /bin/sh -g buildarr -u $PUID buildarr\nexec su-exec buildarr:buildarr buildarr "$@"\n' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["daemon"]
