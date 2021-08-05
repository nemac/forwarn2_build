
import os.path
from util import load_env

load_env(ns=globals())

vols = {
  os.path.realpath(FW2_ARCHIVE_DIR_NORMAL): {
    'bind': os.path.join(DKR_BUILD_DIR, FW2_ARCHIVE_DIR_NORMAL),
    'mode': 'rw'
  },
  os.path.realpath(FW2_ARCHIVE_DIR_MUTED): {
    'bind': os.path.join(DKR_BUILD_DIR, FW2_ARCHIVE_DIR_MUTED),
    'mode': 'rw'
  },
  os.path.realpath('.'): {
    'bind': os.path.realpath(DKR_BUILD_DIR),
    'mode': 'rw'
  },
  os.path.realpath(PRECURSORS_DIR): {
    'bind': os.path.join(DKR_BUILD_DIR, PRECURSORS_DIR),
    'mode': 'rw'
  },
  os.path.realpath(ALL_YEAR_MAXES_DIR): {
    'bind': os.path.join(DKR_BUILD_DIR, ALL_YEAR_MAXES_DIR),
    'mode': 'rw'
  }
}

