#!/usr/bin/env python

import os, os.path, re
import sys, os
import os.path
import argparse
import shutil

base_path = '/mnt/efs/forwarn'

precursor_archive_dir = os.path.join(base_path, 'precursors')

precursor_batch_dir = os.path.join(base_path, 'forwarn2_build_prod/precursors')

jd_pattern = lambda jd: ".*\d{4}\."+jd+".*\.img$"

def move_precursors_to_archive(src):
  for jd in os.listdir(precursor_archive_dir):
    for f in os.listdir(src):
      m = re.search(jd_pattern(jd), f)
      if m:
        src_path = os.path.join(src, f)
        dst_path = os.path.join(precursor_archive_dir, jd, f)
        print("Copying {} to {}...".format(src_path, dst_path))
        if os.path.exists(dst_path):
          os.remove(dst_path)
        shutil.move(src_path, dst_path)


if __name__ == '__main__':
  move_precursors_to_archive(precursor_batch_dir)
