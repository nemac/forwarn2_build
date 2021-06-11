
import docker
import os.path

from util import load_env

load_env()

tag = 'gdal:2.4.2'
dkr_build_dir = '/build'
precursor_dir = './precursors'
graph_data_dir = './graph_data'
name = 'fw2_build'
build_dir = './gdal_docker'
dkr_user = 'nappl_fswms'
dkr_group = 'nappl'


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
  print(gdal_image)


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
  except Exception as e:
    print(e) 


vols = {
  os.path.realpath('.'): {
    'bind': os.path.realpath(dkr_build_dir),
    'mode': 'rw'
  },
  os.path.realpath(precursor_dir): {
    'bind': os.path.join(dkr_build_dir, precursor_dir),
    'mode': 'rw'
  },
  os.path.realpath(graph_data_dir): {
    'bind': os.path.join(dkr_build_dir, graph_data_dir),
    'mode': 'rw'
  }
}

run_gdal('/build/dkr_update', volumes=vols)
