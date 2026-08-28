FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 sudo \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash agent

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv
ENV UV_BREAK_SYSTEM_PACKAGES=1
RUN uv pip install --python /usr/bin/python3 --system 'harbor-rewardkit==0.1.*'

COPY f1/ /opt/f1/
COPY data/formula_1.sqlite /opt/f1/formula_1.sqlite
COPY data/questions.json /opt/f1/questions.json
COPY data/gold.json /opt/f1/gold.json

RUN chmod 755 /opt/f1/f1.py \
    && chmod 600 /opt/f1/formula_1.sqlite /opt/f1/gold.json \
    && chmod 644 /opt/f1/questions.json \
    && printf '%s\n' '#!/bin/sh' 'if [ "$1" = query ]; then shift; fi' 'exec sudo -n /usr/bin/python3 /opt/f1/f1.py query "$@"' > /usr/local/bin/db \
    && chmod 755 /usr/local/bin/db \
    && printf '%s\n' 'agent ALL=(root) NOPASSWD: /usr/bin/python3 /opt/f1/f1.py query *' > /etc/sudoers.d/f1 \
    && chmod 440 /etc/sudoers.d/f1 \
    && mkdir -p /app/sessions \
    && chown -R agent:agent /app

WORKDIR /app
