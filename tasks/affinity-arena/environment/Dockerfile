FROM ubuntu:24.04

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 sudo ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 2000 --create-home --shell /bin/bash agent

COPY arena/ /opt/affinity-arena/arena/
COPY trial.json admin.py /opt/affinity-arena/
COPY public.py /usr/local/libexec/affinity-arena-public
COPY affinity-arena /usr/local/bin/affinity-arena
COPY RULES.md /app/world/RULES.md
RUN chmod 700 /opt/affinity-arena \
    && chmod 755 /usr/local/libexec/affinity-arena-public /usr/local/bin/affinity-arena \
    && printf '%s\n' 'Defaults:agent env_reset, !setenv' \
       'agent ALL=(root) NOPASSWD: /usr/local/libexec/affinity-arena-public' \
       > /etc/sudoers.d/affinity-arena \
    && chmod 440 /etc/sudoers.d/affinity-arena \
    && visudo -cf /etc/sudoers.d/affinity-arena \
    && mkdir -p /app/battles /app/sessions /app/workspace /logs/verifier \
    && touch /app/notes.md \
    && printf '{}\n' > /app/affinity-chart.json \
    && chown agent:agent /app/notes.md /app/affinity-chart.json /app/sessions /app/workspace \
    && chmod 755 /app /app/world /app/battles \
    && chmod 700 /logs/verifier \
    && /usr/bin/python3 -I /opt/affinity-arena/admin.py start 1 > /dev/null

WORKDIR /app
