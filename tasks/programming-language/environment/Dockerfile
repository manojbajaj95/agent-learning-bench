FROM ubuntu:24.04

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 sudo ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 2000 --create-home --shell /bin/bash agent

COPY language_game/ /opt/programming-language/language_game/
COPY trial.json admin.py /opt/programming-language/
COPY public.py /usr/local/libexec/language-public
COPY language-lab /usr/local/bin/language-lab
COPY RULES.md /app/world/RULES.md
RUN chmod 700 /opt/programming-language \
    && chmod 755 /usr/local/libexec/language-public /usr/local/bin/language-lab \
    && printf '%s\n' 'Defaults:agent env_reset, !setenv' \
       'agent ALL=(root) NOPASSWD: /usr/local/libexec/language-public' \
       > /etc/sudoers.d/language-lab \
    && chmod 440 /etc/sudoers.d/language-lab \
    && visudo -cf /etc/sudoers.d/language-lab \
    && mkdir -p /app/problems /app/sessions /app/workspace /logs/verifier \
    && touch /app/notes.md \
    && chown agent:agent /app/notes.md /app/sessions /app/workspace \
    && chmod 755 /app /app/world /app/problems \
    && chmod 700 /logs/verifier \
    && /usr/bin/python3 -I /opt/programming-language/admin.py start 1 > /dev/null

WORKDIR /app
