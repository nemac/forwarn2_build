#!/usr/bin/env python3

import os.path

from volumes import vols
from util import load_env, clean_all, chown_all
from dkr import run_gdal

load_env(ns=globals())

try:
  run_gdal(os.path.join(DKR_BUILD_DIR, 'dkr_update'), volumes=vols)
finally:
  clean_all()

