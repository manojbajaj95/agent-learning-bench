FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 sudo \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash agent

COPY report/ /opt/report/

# `report` is the only way the agent reaches the desk. The engine, the rules and
# the brief bank sit behind sudo in a directory the agent cannot read.
RUN printf '%s\n' '#!/bin/sh' 'exec python3 /opt/report/cli.py "$@"' \
      > /usr/local/bin/report-desk \
    && printf '%s\n' '#!/bin/sh' 'exec sudo -n /usr/local/bin/report-desk "$@"' \
      > /usr/local/bin/report \
    && chmod 700 /usr/local/bin/report-desk \
    && chmod 755 /usr/local/bin/report \
    && printf '%s\n' 'agent ALL=(root) NOPASSWD: /usr/local/bin/report-desk' \
      > /etc/sudoers.d/report-desk \
    && chmod 440 /etc/sudoers.d/report-desk \
    && mkdir -p /opt/report/state /app/world /app/sessions /app/desk \
    && cp /opt/report/RULES.md /app/world/RULES.md \
    && chmod 644 /app/world/RULES.md \
    && touch /app/notes.md \
    && chown -R agent:agent /app \
    && chown -R root:root /opt/report \
    && chmod 700 /opt/report

WORKDIR /app
