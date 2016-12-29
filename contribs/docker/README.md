Dockerfile for XiVO dxtora

## Install Docker

To install docker on Linux :

    curl -sL https://get.docker.io/ | sh
 
 or
 
     wget -qO- https://get.docker.io/ | sh

## Build

To build the image, simply invoke

    docker build -t xivo-dxtora github.com/wazo-pbx/xivo-dxtora

Or directly in the sources in contribs/docker

    docker build -t xivo-dxtora .
  
## Usage

To run the container, do the following:

    docker run -d -v /conf/dxtora:/etc/xivo-dxtora/ xivo-dxtora

On interactive mode :

    docker run -v /conf/dxtora:/etc/xivo-dxtora -it xivo-dxtora bash

After launch xivo-dxtora.

    xivo-dxtora -f -d

## Infos

- Using docker version 1.5.0 (from get.docker.io) on ubuntu 14.04.
- If you want to using a simple webi to administrate docker use : https://github.com/crosbymichael/dockerui

To get the IP of your container use :

    docker ps -a
    docker inspect <container_id> | grep IPAddress | awk -F\" '{print $4}'
