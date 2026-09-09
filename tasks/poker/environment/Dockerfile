FROM ubuntu:24.04

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 sudo \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 2000 --create-home --shell /bin/bash agent

COPY poker_game/ /opt/poker/poker_game/
COPY admin.py /opt/poker/admin.py
COPY public.py /usr/local/libexec/poker-public
COPY poker /usr/local/bin/poker
COPY RULES.md /app/world/RULES.md
RUN chmod 700 /opt/poker \
    && chmod 755 /usr/local/libexec/poker-public /usr/local/bin/poker \
    && printf '%s\n' 'Defaults:agent env_reset, !setenv' \
       'agent ALL=(root) NOPASSWD: /usr/local/libexec/poker-public' \
       > /etc/sudoers.d/poker \
    && chmod 440 /etc/sudoers.d/poker \
    && visudo -cf /etc/sudoers.d/poker \
    && mkdir -p /app/sessions /app/workspace /logs/verifier \
    && chown agent:agent /app/sessions /app/workspace \
    && chmod 755 /app /app/world \
    && chmod 700 /logs/verifier \
    && /usr/bin/python3 -I /opt/poker/admin.py start 1 > /dev/null

WORKDIR /app
