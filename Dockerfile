## Image to build from sources

FROM debian:stretch
MAINTAINER Wazo Maintainers <dev@wazo.community>

ENV DEBIAN_FRONTEND noninteractive
ENV HOME /root

# Add dependencies
RUN apt-get -qq update
RUN apt-get -qq -y install \
    git \
    apt-utils \
    python-pip \
    python-dev

# Install xivo-dxtora
ADD . /usr/src/dxtora
WORKDIR /usr/src/dxtora
RUN pip install -r requirements.txt
RUN python setup.py install

# Configure environment
RUN mkdir /var/lib/xivo-dxtora \
    && touch /var/log/xivo-dxtora.log \
    && adduser --quiet --system --group --no-create-home xivo-dxtora \
    && chown xivo-dxtora:xivo-dxtora /var/log/xivo-dxtora.log \
    && install -d -o xivo-dxtora -g xivo-dxtora /var/run/xivo-dxtora \
    && cp -r etc/xivo-dxtora /etc

# Clean
WORKDIR /root
RUN rm -rf /usr/src/dxtora
RUN apt-get clean

CMD ["xivo-dxtora", "-f"]
