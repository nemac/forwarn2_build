#!/usr/bin/env python

import datetime
import argparse, os, os.path, sys
import logging
from subprocess import Popen, PIPE, STDOUT

ALL_PRODUCT_DAYS_FILE = 'all_product_days'


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


def setup_arg_parser():
  parser = argparse.ArgumentParser()
  parser.add_argument('-y', '--year', help='Year to glob files against')
  return parser


def get_year_netcdf_files(year):
  all_nc_files = [ f for f in os.listdir('.') if year in f and f.endswith('.nc') ]
  with open(ALL_PRODUCT_DAYS_FILE) as f:
    all_product_days = [ line.rstrip() for line in f.readlines() ]
  is_good = True
  nc_files = []
  for day in all_product_days:
    for f in all_nc_files:
      if day in f and f not in nc_files:
        nc_files.append(f)
  nc_files = sorted(nc_files)
  print(nc_files)
  if not is_good:
    logging.error("We're either missing a day or the file list is not sorted correctly.")
    logging.error("List of files:")
    logging.error(nc_files)
    logging.error('Exiting...')
    sys.exit(1)
  return nc_files
 

def main():
  parser = setup_arg_parser()
  args = parser.parse_args()
  year = args.year
  log_path = setup_logging()
  if not year:
    logging.error('Must pass a year!')
    sys.exit(1)
  if len(year) != 4:
    logging.error('Year must be 4 digits long!')
    sys.exit(1)
  nc_files = get_year_netcdf_files(year)
  filename = 'maxMODIS.{0}.std.nc'.format(year)
  c = [ 'ncecat', '-A' ]
  c.extend(nc_files)
  c.append(filename)
  print(' '.join(c))
  process = Popen(c, stdout=PIPE, stderr=STDOUT)
  with process.stdout:
    log_subprocess_output(process.stdout)
  exitcode = process.wait()


if __name__ == '__main__':
  main()
