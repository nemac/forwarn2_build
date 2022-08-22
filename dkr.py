
import os, os.path, pwd, grp
import docker
import logging as log

from util import load_env


load_env(ns=globals())

def build_gdal():
  client = docker.from_env()
  user = pwd.getpwnam(DKR_USER)
  group = grp.getgrnam(DKR_GROUP)
  user_id = user[2]
  group_id = group[2]
  gdal_image = client.images.build(
    path=DKR_BUILD_DIR_HOST,
    tag=DKR_IMAGE_TAG,
    buildargs={
      'DKR_BUILD_DIR': DKR_BUILD_DIR,
      'DKR_USER': DKR_USER,
      'DKR_GROUP': DKR_GROUP,
      'DKR_USER_ID': str(user_id),
      'DKR_GROUP_ID': str(group_id)
    }
  )


def run_gdal(cmd, volumes=None):
  client = docker.from_env()
  try:
    container = client.containers.run(DKR_IMAGE_TAG,
        command=cmd,
        name=DKR_CONTAINER_NAME,
        network_mode='host',
        auto_remove=True,
        volumes=volumes,
        tty=True,
        detach=True,
    )
    for chunk in container.logs(stream=True):
      print(chunk.decode('UTF-8'), end='')
    container.wait()
  except Exception as e:
    log.error(e) 


