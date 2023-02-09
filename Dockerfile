FROM python:3.9-slim-bullseye AS compile-image
LABEL maintainer="Wazo Maintainers <dev@wazo.community>"

RUN python -m venv /opt/venv
# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /usr/src/wazo-dxtora
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY setup.py setup.py
COPY wazo_dxtora wazo_dxtora
RUN python setup.py install

FROM python:3.9-slim-bullseye AS build-image
COPY --from=compile-image /opt/venv /opt/venv

COPY ./etc/wazo-dxtora /etc/wazo-dxtora

RUN true \
    && adduser --quiet --system --group --home /var/lib/wazo-dxtora wazo-dxtora \
    && install -o wazo-dxtora -g wazo-dxtora /dev/null /var/log/wazo-dxtora.log \
    && install -d -o wazo-dxtora -g wazo-dxtora /run/wazo-dxtora

# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"
CMD ["wazo-dxtora"]
