
import docker
import os.path

from config import *

from util import load_env

load_env()


def build_gdal():
  client = docker.from_env()
  gdal_image = client.images.build(
    path=build_dir,
    tag=tag,
    buildargs={
      'DKR_USER': dkr_user,
      'DKR_GROUP': dkr_group,
      'DKR_BUILD_DIR': dkr_build_dir
    }
  )


def run_gdal(cmd, name=name, volumes=None):
  client = docker.from_env()
  containers = client.containers.list()
  if name in [ c.name for c in containers ]:
    print("Already running!")
    return
  try:
    container = client.containers.run(tag,
        command=cmd,
        name=name,
        network_mode='host',
        auto_remove=True,
        volumes=volumes,
        tty=True,
        detach=True
    )
    for chunk in container.logs(stream=True):
      print(chunk.decode('UTF-8'), end='')
    print()
    container.wait()
    print('Done!')
  except Exception as e:
    print(e) 


