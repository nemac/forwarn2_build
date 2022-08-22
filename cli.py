#!/usr/bin/env python3

import os.path, sys

from volumes import vols
from util import load_env, clean_all, chown_all, init_log
from dkr import run_gdal
import docker
import logging as log

load_env(ns=globals())

client = docker.from_env()
containers = client.containers.list()
if DKR_CONTAINER_NAME in [ c.name for c in containers ]:
  init_log()
  log.info("FW2 production is already running! Exiting...")
  sys.exit()

try:
  run_gdal(os.path.join(DKR_BUILD_DIR, 'dkr_update'), volumes=vols)
finally:
  clean_all()

