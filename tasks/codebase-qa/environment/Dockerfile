FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash agent

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv
ENV UV_BREAK_SYSTEM_PACKAGES=1
RUN uv pip install --python /usr/bin/python3 --system 'harbor-rewardkit==0.1.*'

COPY qa/ /opt/qa/
COPY data/questions.json /opt/qa/questions.json
COPY data/gold.json /opt/qa/gold.json
COPY data/repo/ /data/repo/

RUN chmod 755 /opt/qa/qa.py \
    && chmod 600 /opt/qa/gold.json \
    && chmod 644 /opt/qa/questions.json \
    && chmod -R a+rX /data/repo \
    && chmod -R a-w /data/repo \
    && mkdir -p /app/sessions \
    && chown -R agent:agent /app

WORKDIR /app
