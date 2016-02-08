## Image to build from sources

FROM debian:jessie
MAINTAINER XiVO Team "dev@avencall.com"

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
WORKDIR /usr/src
ADD . /usr/src/dxtora
WORKDIR dxtora
RUN pip install -r requirements.txt
RUN python setup.py install

# Configure environment
RUN touch /var/log/xivo-dxtora.log
RUN mkdir /var/lib/xivo-dxtora
WORKDIR /root

# Clean
RUN apt-get clean
RUN rm -rf /usr/src/dxtora

CMD ["xivo-dxtora", "-f"]
