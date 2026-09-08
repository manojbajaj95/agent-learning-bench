FROM node:24-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates \
        chromium \
        fonts-liberation \
        util-linux \
        procps \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash agent

ENV HOME=/home/agent
ENV AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium
ENV AGENT_BROWSER_SESSION=webarena-shopping

RUN pip3 install --break-system-packages --no-cache-dir 'webarena-verified==1.2.3' \
    && npm install -g 'agent-browser@0.36.0'

RUN mkdir -p /app /opt/webarena /logs/agent /logs/verifier \
        /home/agent/.agents/skills \
    && cp -R "$(npm root -g)/agent-browser/skills/agent-browser" \
       /home/agent/.agents/skills/agent-browser \
    && printf '%s\n' '{"args":["--no-sandbox","--disable-dev-shm-usage"]}' \
       > /home/agent/agent-browser.json \
    && touch /app/notes.md

COPY webarena/runtime.py /opt/webarena/runtime.py
COPY data/ /opt/webarena/

RUN test -f /opt/webarena/webarena-verified.json \
    && test -f /opt/webarena/agent-input.json \
    && mv /opt/webarena/webarena-verified.json /opt/webarena/dataset.json \
    && chown -R root:root /opt/webarena /logs/verifier \
    && chown -R agent:agent /app /logs/agent /home/agent \
    && chmod -R a-w /home/agent/.agents/skills/agent-browser \
    && chgrp agent /opt/webarena \
    && chmod 750 /opt/webarena \
    && chmod 755 /opt/webarena/runtime.py \
    && chmod 644 /opt/webarena/agent-input.json \
    && chmod 600 /opt/webarena/dataset.json

ENV WEBARENA_SHOPPING_URL=http://host.docker.internal:7770
ENV WEBARENA_CONTROL_URL=http://host.docker.internal:7772
WORKDIR /app
