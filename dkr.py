
import docker
import os.path

from util import load_env

import logging as log

load_env(ns=globals())

def build_gdal():
  client = docker.from_env()
  gdal_image = client.images.build(
    path=DKR_BUILD_DIR_HOST,
    tag=DKR_IMAGE_TAG,
    buildargs={
      'DKR_USER': DKR_USER,
      'DKR_GROUP': DKR_GROUP,
      'DKR_BUILD_DIR': DKR_BUILD_DIR
    }
  )


def run_gdal(cmd, volumes=None):
  client = docker.from_env()
  containers = client.containers.list()
  if DKR_CONTAINER_NAME in [ c.name for c in containers ]:
    log.info("Already running!")
    return
  try:
    container = client.containers.run(DKR_IMAGE_TAG,
        command=cmd,
        name=DKR_CONTAINER_NAME,
        network_mode='host',
        auto_remove=True,
        volumes=volumes,
        tty=True,
        detach=True
    )
    for chunk in container.logs(stream=True):
      print(chunk.decode('UTF-8'), end='')
    container.wait()
  except Exception as e:
    log.error(e) 


