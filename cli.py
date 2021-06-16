from dkr import run_gdal

vols = {
  os.path.realpath('./ForWarn2'): {
    'bind': os.path.join(dkr_build_dir, 'ForWarn2'),
    'mode': 'rw'
  },
  os.path.realpath('./ForWarn2_Sqrt'): {
    'bind': os.path.join(dkr_build_dir, 'ForWarn2_Sqrt'),
    'mode': 'rw'
  },
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
