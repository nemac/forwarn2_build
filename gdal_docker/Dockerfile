FROM ubuntu:18.04

ARG DKR_BUILD_DIR
ARG DKR_USER
ARG DKR_GROUP
ARG DKR_USER_ID
ARG DKR_GROUP_ID

MAINTAINER NEMAC Dev Team <nemac@unca.edu>

# SMTP
EXPOSE 587
EXPOSE 25
# HTTP
EXPOSE 80

RUN groupadd -g ${DKR_GROUP_ID} ${DKR_GROUP} && \
    useradd -l -u ${DKR_USER_ID} -g ${DKR_GROUP_ID} ${DKR_USER}

WORKDIR $DKR_BUILD_DIR

ADD ./install $DKR_BUILD_DIR/install
ADD ./requirements.txt $DKR_BUILD_DIR/requirements.txt

RUN ./install
