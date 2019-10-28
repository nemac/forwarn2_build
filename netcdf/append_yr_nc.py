#!/usr/bin/env python

import datetime
import argparse, os, os.path, sys
import logging
from subprocess import Popen, PIPE, STDOUT


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
  parser.add_option('--nrt', action="store_true", help="Append to NRT year file")
  parser.add_option('--std', action="store_false", help="Append to STD year file")
  return parser


def get_todo_days_path(prod_type):
  if prod_type == 'std':
    return STD_TODO_DAYS_PATH
  if prod_type == 'nrt':
    return NRT_TODO_DAYS_PATH


def get_all_todo_days(prod_type):
  todo_days_path = get_todo_days_path(prod_type)
  days = []
  with open(todo_days_path) as f:
    for jd in f:
      days.append(jd.strip())
  return days


def write_new_todo_days_file(prod_type, days_to_remove, dryrun):
  logging.info('Writing new todo_product_days file...\n')
  days = get_all_todo_days()
  days = [ d for d in days if d not in days_to_remove ]
  new_file_contents = ''
  for day in days:
    new_file_contents += '{0}\n'.format(day)
  if not dryrun:
    with open(get_todo_days_path(prod_type), 'w') as f:
      f.write(new_file_contents)
  else:
    logging.info("Since this is a dryrun we're not going to write a new todo_product_days file. But just for fun, this is what the contents of the new file would be:\n{0}".format(new_file_contents))


def get_8day_nc_files_for(year, prod_type):
  all_nc_files = [ f for f in os.listdir('.') if year in f and prod_type in f and f.endswith('.nc') ]
  with open(get_todo_days_path(prod_type) as f:
    all_product_days = [ line.rstrip() for line in f.readlines() ]
  nc_files = []
  for day in all_product_days:
    for f in all_nc_files:
      if day in f and f not in nc_files:
        nc_files.append(f)
  nc_files = sorted(nc_files)
  logging.info("List of files to append:")
  logging.info(nc_files)
  return nc_files
 

def main():
  parser = setup_arg_parser()
  args = parser.parse_args()
  year = args.year
  is_nrt = args.nrt
  is_std = args.std
  log_path = setup_logging()
  if (is_nrt and is_std) or (not is_nrt and not is_std):
    logging.error("You must supply either the --nrt flag or the --std flag")
    sys.exit(1)
  if not year:
    logging.error('Must pass a year!')
    sys.exit(1)
  if len(year) != 4:
    logging.error('Year must be 4 digits long!')
    sys.exit(1)
  if is_nrt:
    prod_type = 'nrt'
  elif is_std:
    prod_type = 'std' 
  nc_files = get_8day_nc_files_for(year, prod_type)
  filename = 'maxMODIS.{0}.std.nc'.format(year)
  c = [ 'ncecat', '-A' ]
  c.extend(nc_files)
  c.append(filename)
  logging.info(' '.join(c))
  process = Popen(c, stdout=PIPE, stderr=STDOUT)
  with process.stdout:
    log_subprocess_output(process.stdout)
  exitcode = process.wait()


if __name__ == '__main__':
  main()
