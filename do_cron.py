#!/usr/bin/env python

import sys, traceback
import logging as log

# TODO import only what you need
from config import *
from util import *
from fw2_build import *


# TODO separate log files, remove log files if nothing happened
init_log()


def main():
  new_stds = build_all_8day_max_files_for_product_type('std')
  new_nrts = build_all_8day_max_files_for_product_type('nrt')
  years_with_missing_all_year_maxes = get_todo_years_missing_all_year_maxes_precursor()
  years_to_build = [ d['year'] for d in new_stds ]
  years_to_build.extend(years_with_missing_all_year_maxes)
  for year in sorted(set(years_to_build)):
    build_all_year_maxes_tif_for(year)
  delete_nrt_8day_max_files_with_existing_std()
  fw2_todo_dates = get_todo_dates_fw2_products()
  symlink_precursors(fw2_todo_dates)
  for d in fw2_todo_dates:
    build_fw2_products_for(d, dryrun=False, is_cli_run=False, log_path='./log', email_results=True)
  archive_new_precursors()


if __name__ == '__main__':
  try:
    main()
  except:
    log.error(traceback.print_exc())
  finally:
    destroy_symlinks_by_ext()
