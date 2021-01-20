#!/bin/bash

source .env

docker build -t $DKR_IMAGE_TAG .
