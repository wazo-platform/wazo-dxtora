## Image to build from sources

FROM debian:buster
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

# Install wazo-dxtora
ADD . /usr/src/dxtora
WORKDIR /usr/src/dxtora
RUN pip install -r requirements.txt
RUN python setup.py install

# Configure environment
RUN mkdir /var/lib/wazo-dxtora \
    && touch /var/log/wazo-dxtora.log \
    && adduser --quiet --system --group --no-create-home wazo-dxtora \
    && chown wazo-dxtora:wazo-dxtora /var/log/wazo-dxtora.log \
    && install -d -o wazo-dxtora -g wazo-dxtora /var/run/wazo-dxtora \
    && cp -r etc/wazo-dxtora /etc

# Clean
WORKDIR /root
RUN rm -rf /usr/src/dxtora
RUN apt-get clean

CMD ["wazo-dxtora", "-f"]
