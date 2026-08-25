FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

COPY tally/ /opt/tally/
RUN chmod +x /opt/tally/game.py \
    && mkdir -p /app/world \
    && cp /opt/tally/RULES.md /app/world/RULES.md

WORKDIR /app
