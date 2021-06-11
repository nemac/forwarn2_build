#!/usr/bin/env python3

import os, os.path, sys, re, datetime, shutil, traceback, argparse

import xml.etree.ElementTree as ET
import rasterio as rio
import logging as log
from subprocess import check_output

from util import \
  ALL_MODIS_JULIAN_DAYS, \
  load_env, \
  mail_results, \
  harvest_products, \
  init_log, \
  try_func, \
  run_subprocess, \
  archive_new_precursors, \
  make_symlinks_for_dates, \
  get_now_est, \
  get_default_log_path

from state import \
  get_todo_dates_8day_max, \
  get_todo_years_missing_all_year_maxes_precursor, \
  get_three_modis_dates_for_fw2_product, \
  get_todo_dates_fw2_products, \
  delete_nrt_8day_max_files_with_existing_std, \
  delete_symlinks_by_ext, \
  check_is_only_instance_or_quit, \
  fw2_products_exist

def get_cli_args():
  '''Initialize the command-line argument-parser.'''
  default_log_path = LOG_PATH_TEMPLATE.format(r''+LOG_FILE_TIMESTAMP_FORMAT)
  log.info('default_log_path: ', default_log_path)
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--cron', action='store_true', help='Run the full ForWarn 2 task cycle (a normal cron job). Implies --harvest, --email, and --log. The --datestring flag will be ignored.')
  parser.add_argument('--dryrun', action='store_true', help='Run the script with no side effects.')
  # TODO
  parser.add_argument('--harvest', action='store_true', help='TODO Move ForWarn 2 products output by dodate into the local product directories into the ForWarn 2 product archive.')
  parser.add_argument('-d', '--datestring', help='TODO Build ForWarn 2 products for a certain date. The argument is of form YYYYDOY, where YYYY is a year and DOY is a day of the year, padded with zeroes if necessary. For example, 2021001 builds the ForWarn 2 product set for day 1 of 2021.')
  parser.add_argument('--email', action='store_true', help='TODO Email the results to addresses in mail_to_addrs.txt')
  parser.add_argument('--overwrite', action='store_true', help='TODO Overwrite existing products. Use at your own risk!')
  parser.add_argument('--log', action='store_true', help='TODO Keep a log. Use --log-path to override the default log path, which places the log in ./log.')
  parser.add_argument('--log-path', help='TODO Path to override the default log file (implies --log).')
  parser.add_argument('--log-level', help='Set the Python logging level.', \
    choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], \
    metavar='(CRITICAL|ERROR|WARNING|INFO|DEBUG)' \
  )
  args = parser.parse_args()
  return args


def main():
  check_is_only_instance_or_quit()
  load_env(ns=globals())
  args = get_cli_args()
  now = get_now_est(time_format='%Y%m%d_%I:%M:%S')
  if args.log or args.cron:
    log_path = get_default_log_path()
  if args.log_path:
    log_path = args.log_path
  if args.log_level:
    level = getattr(log, args.log_level)
  else:
    level = log.DEBUG
  init_log(level=level, log_path=log_path, dryrun=args.dryrun)
  if args.cron:
    all_tasks(log_path, dryrun=args.dryrun, email=args.email, harvest=True)
  elif args.datestring:
    year = datestring[:4]
    jd = datestring[-3:]
    # TODO
    #try_func(validate_modis_yr_jd, year, jd, quit_on_fail=True)



########################### HELPERS ###################################




if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    log.error(e.__str__())
    tb_lines = [ line.strip() for line in traceback.format_tb(e.__traceback__) ]
    for line in tb_lines:
      log.error(line)
  finally:
    delete_symlinks_by_ext()

