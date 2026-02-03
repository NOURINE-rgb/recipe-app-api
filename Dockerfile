FROM python:3.12-alpine3.19

ENV PYTHONUNBUFFERED=1

COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt
COPY ./scripts /scripts
COPY ./app /app
WORKDIR /app
EXPOSE 8000

ARG DEV=false

RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    apk add --no-cache \
        postgresql-client \
        jpeg-dev \
        build-base \
        postgresql-dev \
        musl-dev \
        zlib-dev \
        linux-headers && \
    /py/bin/pip install -r /tmp/requirements.txt && \
    if [ "$DEV" = "true" ]; then \
        /py/bin/pip install -r /tmp/requirements.dev.txt ; \
    fi && \
    rm -rf /tmp && \
    adduser --disabled-password --no-create-home django-user && \
    mkdir -p /vol/web/media /vol/web/static && \
    chown -R django-user:django-user /vol && \
    chmod -R 755 /vol && \
    chmod -R +x /scripts

ENV PATH="/scripts:/py/bin:$PATH"
USER django-user

CMD ["run.sh"]
