FROM ubuntu:18.04

MAINTAINER NEMAC Dev Team <nemac@unca.edu>

USER root

EXPOSE 80

WORKDIR /build

ADD ./install.sh /build/install.sh

RUN ./install.sh
