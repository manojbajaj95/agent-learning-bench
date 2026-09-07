FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 sudo \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash agent

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv
ENV UV_BREAK_SYSTEM_PACKAGES=1
RUN uv pip install --python /usr/bin/python3 --system 'harbor-rewardkit==0.1.*'

COPY web/ /opt/web/
COPY data/questions.json /opt/web/questions.json
COPY data/gold.json /opt/web/gold.json

RUN chmod 755 /opt/web/web.py \
    && chmod 600 /opt/web/pages.py /opt/web/gold.json \
    && chmod 644 /opt/web/questions.json \
    && mkdir -p /opt/web/state \
    && chmod 700 /opt/web/state \
    && printf '%s\n' '#!/bin/sh' 'cmd=$1; shift' \
       'exec sudo -n /usr/bin/python3 /opt/web/web.py "$cmd" "$@"' \
       > /usr/local/bin/web \
    && chmod 755 /usr/local/bin/web \
    && printf '%s\n' \
       'agent ALL=(root) NOPASSWD: /usr/bin/python3 /opt/web/web.py get *, /usr/bin/python3 /opt/web/web.py post *' \
       > /etc/sudoers.d/web \
    && chmod 440 /etc/sudoers.d/web \
    && mkdir -p /app/sessions \
    && chown -R agent:agent /app

WORKDIR /app
