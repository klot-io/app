FROM arm32v7/python:3.8.5-alpine3.12

RUN apk add git &mkdir -p /opt/klot-io

WORKDIR /opt/klot-io

COPY requirements.txt .

RUN apk add --no-cache --virtual .pip-deps  \
        gcc \
        libc-dev \
        make \
        git \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del --no-network .pip-deps \
	&& find /usr/local -depth \
		\( \
			\( -type d -a \( -name test -o -name tests -o -name idle_test \) \) \
			-o \
			\( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
		\) -exec rm -rf '{}' +

ENV PYTHONPATH "/opt/klot-io/lib:${PYTHONPATH}"
