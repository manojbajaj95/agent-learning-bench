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
ENV WEBCMD_PROFILE=webarena

RUN pip3 install --break-system-packages --no-cache-dir 'webarena-verified==1.2.3' \
    && npm install -g '@agentrhq/webcmd@0.8.2'

RUN mkdir -p /app /opt/webarena /logs/agent /logs/verifier \
        /home/agent/.agents/skills \
    && cp -R "$(npm root -g)/@agentrhq/webcmd/skills/webcmd-browser" \
       /home/agent/.agents/skills/webcmd-browser \
    && touch /app/notes.md

COPY webarena/chromium-wrap.sh /opt/webarena/chromium-wrap.sh
COPY webarena/har_recorder.mjs /opt/webarena/har_recorder.mjs
COPY webarena/runtime.py /opt/webarena/runtime.py
COPY data/ /opt/webarena/

RUN chmod 755 /opt/webarena/chromium-wrap.sh /opt/webarena/har_recorder.mjs \
        /opt/webarena/runtime.py

USER agent
RUN webcmd setup --browser /opt/webarena/chromium-wrap.sh \
    && python3 -c "import json; from pathlib import Path; p=Path.home()/'.webcmd'/'config.json'; c=json.loads(p.read_text()); c['browser']['kind']='chrome'; p.write_text(json.dumps(c, indent=2)+'\n')" \
    && webcmd profile create webarena

USER root
RUN test -f /opt/webarena/webarena-verified.json \
    && test -f /opt/webarena/agent-input.json \
    && mv /opt/webarena/webarena-verified.json /opt/webarena/dataset.json \
    && chown -R root:root /opt/webarena /logs/verifier \
    && chown -R agent:agent /app /logs/agent /home/agent \
    && chmod -R a-w /home/agent/.agents/skills/webcmd-browser \
    && chgrp agent /opt/webarena \
    && chmod 750 /opt/webarena \
    && chmod 644 /opt/webarena/agent-input.json \
    && chmod 600 /opt/webarena/dataset.json

ENV WEBARENA_SHOPPING_URL=http://host.docker.internal:7770
ENV WEBARENA_CONTROL_URL=http://host.docker.internal:7772
WORKDIR /app
