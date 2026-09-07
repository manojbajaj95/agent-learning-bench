FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl python3 \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash agent

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv
ENV UV_BREAK_SYSTEM_PACKAGES=1
RUN uv pip install --python /usr/bin/python3 --system 'webarena-verified==1.2.3' \
    && npm install -g 'agent-browser@0.36.0' \
    && agent-browser install --with-deps

RUN mkdir -p /app/.pi/skills /app/sessions /opt/webarena /logs/agent /logs/verifier \
    && cp -R "$(npm root -g)/agent-browser/skills/agent-browser" \
       /app/.pi/skills/agent-browser

COPY webarena/runtime.py /opt/webarena/runtime.py
COPY data/ /opt/webarena/

RUN mv /opt/webarena/webarena-verified.json /opt/webarena/dataset.json \
    && printf '%s\n' \
       '{"test_data_file":"/opt/webarena/dataset.json","environments":{"__SHOPPING__":{"urls":["http://host.docker.internal:7770"]}}}' \
       > /opt/webarena/config.json \
    && chown -R root:root /opt/webarena /logs/verifier \
    && chown -R agent:agent /app /logs/agent \
    && chgrp agent /opt/webarena \
    && chmod 750 /opt/webarena \
    && chmod 755 /opt/webarena/runtime.py \
    && chmod 644 /opt/webarena/agent-input.json \
    && chmod 600 /opt/webarena/dataset.json /opt/webarena/config.json \
    && if [ -f /opt/webarena/auth.json ]; then \
         chgrp agent /opt/webarena/auth.json; chmod 640 /opt/webarena/auth.json; \
       fi

ENV AGENT_BROWSER_SESSION=webarena-shopping
ENV WEBARENA_SHOPPING_URL=http://host.docker.internal:7770
ENV WEBARENA_CONTROL_URL=http://host.docker.internal:7771
ENV WEBARENA_AUTH_STATE=/opt/webarena/auth.json

WORKDIR /app
