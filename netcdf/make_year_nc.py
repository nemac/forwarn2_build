#!/usr/bin/env python

import datetime
import argparse, os, os.path, sys
import logging
from subprocess import Popen, PIPE, STDOUT

from Config import *

def pad_with_zero(num):
  num = int(num)
  return str(num) if num > 9 else '0{0}'.format(num)


def log_subprocess_output(pipe):
  for line in iter(pipe.readline, b''):
    logging.info(str(line))


def setup_logging():
  now = datetime.datetime.now()
  month = pad_with_zero(now.month)
  day = pad_with_zero(now.day)
  hour = pad_with_zero(now.hour)
  minute = pad_with_zero(now.minute)
  second = pad_with_zero(now.second)

  log_filename = 'log_{0}{1}{2}_{3}h{4}m{5}s.log'.format(now.year, month, day, hour, minute, second)
  log_path = os.path.join(log_filename)
  logging.basicConfig(filename=log_path, level=logging.DEBUG)
  logger = logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
  return log_path


def log_subprocess_output(pipe):
  for line in iter(pipe.readline, b''):
    logging.info(str(line))


def is_filelist_contiguous(filelist, all_product_days, year):
  for i, day in enumerate(all_product_days):
    if i == len(filelist):
      break
    if '{0}.{1}'.format(year, day) not in filelist[i]:
      return False 
  return True


def get_year_netcdf_files(year):
  all_nc_files = [ f for f in os.listdir(STD_DAY_FILES_PATH) if year in f and 'std' in f and f.endswith('.nc') ]
  with open(ALL_DAYS_PATH) as f:
    all_product_days = [ line.rstrip() for line in f.readlines() ]
  nc_files = []
  for day in all_product_days:
    for f in all_nc_files:
      if day in f and f not in nc_files:
        nc_files.append(f)
  nc_files = sorted(nc_files)
  if not is_filelist_contiguous(nc_files, all_product_days, year):
    logging.error("We're either missing a day or the file list is not sorted correctly.")
    logging.error("List of files:")
    logging.error(nc_files)
    logging.error('Exiting...')
    sys.exit(1)
  return nc_files
 

def setup_arg_parser():
  parser = argparse.ArgumentParser()
  parser.add_argument('-y', '--year', help='Year to glob files against')
  parser.add_argument('--dryrun', action='store_true')
  return parser


def make_netcdf(year, dryrun):
  nc_files = get_year_netcdf_files(year)
  nc_file_paths = list(map(lambda f: os.path.join(STD_DAY_FILES_PATH, f), nc_files))
  filename = 'maxMODIS.{0}.std.nc'.format(year)
  c = [ 'ncecat', '-A' ]
  c.extend(nc_file_paths)
  c.append(filename)
  logging.info(' '.join(c))
  if not dryrun:
    process = Popen(c, stdout=PIPE, stderr=STDOUT)
    with process.stdout:
      log_subprocess_output(process.stdout)
    exitcode = process.wait()


def main():
  parser = setup_arg_parser()
  args = parser.parse_args()
  year = args.year
  dryrun = args.dryrun
  log_path = setup_logging()
  if not year:
    logging.error('Must pass a year!')
    sys.exit(1)
  if len(year) != 4:
    logging.error('Year must be 4 digits long!')
    sys.exit(1)
  make_netcdf(year, dryrun)

if __name__ == '__main__':
  main()
