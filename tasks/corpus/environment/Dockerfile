FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 unzip \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash agent

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv
ENV UV_BREAK_SYSTEM_PACKAGES=1
RUN uv pip install --python /usr/bin/python3 --system 'harbor-rewardkit==0.1.*'

COPY corpus/ /opt/corpus/
COPY data/questions.json /opt/corpus/questions.json
COPY data/gold.json /opt/corpus/gold.json
COPY data/confluence_slice_0001.zip /tmp/confluence_slice_0001.zip
COPY data/confluence_slice_0002.zip /tmp/confluence_slice_0002.zip

RUN mkdir -p /data/corpus /tmp/c \
    && unzip -q /tmp/confluence_slice_0001.zip -d /tmp/c \
    && unzip -q /tmp/confluence_slice_0002.zip -d /tmp/c \
    && mv /tmp/c/confluence/* /data/corpus/ \
    && rm -rf /tmp/c /tmp/confluence_slice_0001.zip /tmp/confluence_slice_0002.zip \
    && chmod 755 /opt/corpus/corpus.py \
    && chmod 600 /opt/corpus/gold.json \
    && chmod 644 /opt/corpus/questions.json \
    && chmod -R a+rX /data/corpus \
    && chmod -R a-w /data/corpus \
    && mkdir -p /app/sessions \
    && chown -R agent:agent /app

WORKDIR /app
