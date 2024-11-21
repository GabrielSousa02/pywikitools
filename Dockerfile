FROM 4training/mediawiki:latest

ENV PYTHONUNBUFFERED=1

COPY ./requirements.txt /tmp/requirements.txt

RUN set -eux; \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice \
    python3 \
    python3-pip \
    python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN python3 -m venv /py && \
	/py/bin/pip install --upgrade pip && \
	/py/bin/pip install -r /tmp/requirements.txt

# Install python3-uno and link it to my venv
RUN set -eux; \
    apt-get install -y --no-install-recommends python3-uno

# Symlink the system wide packages into the virtualenv
RUN ln -s /usr/lib/python3/dist-packages/uno.py /py/lib/python*/site-packages/
RUN ln -s /usr/lib/python3/dist-packages/unohelper.py /py/lib/python*/site-packages/

# Set up php-handler for correctbot-handler
COPY ./php-handler/handler.php /var/www/html/correctbot-handler/
COPY ./php-handler/.ht.config.example.json /var/www/html/correctbot-handler/.ht.config.json
RUN sed -ie "s|\"run\": \"/path/to/python /path/to-script.py\"|\"run\": \"/py/bin/python3 /src/correct_bot.py\"|" /var/www/html/correctbot-handler/.ht.config.json


# Set up php-handler for translateodt
COPY ./php-handler/handler.php /var/www/html/translateodt-handler/
COPY ./php-handler/.ht.config.example.json /var/www/html/translateodt-handler/.ht.config.json
RUN sed -ie "s|\"description\": \"Correctbot\"|\"description\": \"TranslateODT\"|" /var/www/html/translateodt-handler/.ht.config.json
RUN sed -ie "s|\"run\": \"/path/to/python /path/to-script.py\"|\"run\": \"/py/bin/python3 /src/translateodt.py\"|" /var/www/html/translateodt-handler/.ht.config.json

# Update the /var/www/html/mediawiki/LocalSettings.php file to have the updated path for the scripts
RUN sed -ie "s|\$wgForTrainingToolsCorrectBotUrl = '/handler/handler.php'|\$wgForTrainingToolsCorrectBotUrl = '/correctbot-handler/handler.php';|" /var/www/html/mediawiki/LocalSettings.php
RUN sed -ie "s|\$wgForTrainingToolsGenerateOdtUrl = '/handler/handler.php'|\$wgForTrainingToolsGenerateOdtUrl = '/translateodt-handler/handler.php';|" /var/www/html/mediawiki/LocalSettings.php

RUN adduser --disabled-password --no-create-home \
		django-user && \
    chown -R django-user:django-user /src

USER django-user
