ARG BUILD_ARCH
FROM ghcr.io/home-assistant/${BUILD_ARCH}-base-python:3.13-alpine3.23


RUN python -m venv /opt/venv \
     && /opt/venv/bin/pip install -U --no-cache-dir "cremalink==0.1.0b11"

WORKDIR /opt/cremalink

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
