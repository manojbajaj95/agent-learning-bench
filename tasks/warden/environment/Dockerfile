FROM ubuntu:24.04

ENV SDL_VIDEODRIVER=dummy
ENV PYGAME_HIDE_SUPPORT_PROMPT=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pygame \
    && rm -rf /var/lib/apt/lists/*

COPY warden/ /opt/warden/
RUN chmod +x /opt/warden/cli.py \
    && printf '%s\n' '#!/bin/sh' 'exec python3 /opt/warden/cli.py "$@"' \
       > /usr/local/bin/warden \
    && chmod +x /usr/local/bin/warden \
    && mkdir -p /app/world /app/sessions /app/fights \
    && cp /opt/warden/RULES.md /app/world/RULES.md

WORKDIR /app
