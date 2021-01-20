#!/usr/bin/env bash

apt-get update && \
apt-get install -y \
  software-properties-common

add-apt-repository -y ppa:ubuntugis/ppa

apt-get update && \
apt-get install -y \
  gdal-bin=2.4.2+dfsg-1~bionic0 \

apt-get update && \
apt-get install -y \
  python-gdal \
  python3-pip \
  wget

pip3 install rasterio
