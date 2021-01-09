#!/usr/bin/env python

import os, sys, os.path, datetime, argparse, logging
from Config import *
from make_year_nc import make_netcdf
from subprocess import check_output

def pad_with_zero(num):
  num = int(num)
  return str(num) if num > 9 else '0{0}'.format(num)


def get_all_todo_days():
  days = []
  with open(ALL_DAYS_PATH) as f:
    for jd in f:
      days.append(jd.strip())
  return days


def get_todo_dates():
  days = get_all_todo_days() # TODO: test this!
  today = datetime.datetime.today()
  today = today.strftime('%Y%j')
  today = datetime.datetime.strptime(today, '%Y%j')
  dates = map(lambda day: datetime.datetime.strptime('{0}{1}'.format(YEAR, day), '%Y%j'), days)
  dates = filter(lambda d: d <= today - datetime.timedelta(days=8), dates)
  dates = map(lambda d: d.strftime('%Y%j'), dates)
  dates = list(dates)
  dates = filter(lambda d: not max_file_exists('std', d), dates)
  return dates


def get_8day_prod_dir(prod_type):
  return STD_DAY_FILES_PATH if prod_type == 'std' else NRT_DAY_FILES_PATH



def max_file_exists(prod_type, d):
  doy_str = '%03d' % int(d[4:])
  f = 'maxMODIS.{0}.{1}.{2}.nc'.format(d[0:4], doy_str, prod_type)
  prod_dir = get_8day_prod_dir(prod_type)
  return os.path.exists(os.path.join(prod_dir, f))


def year_file_exists(year):
  return os.path.exists(os.path.join(NETCDF_YEAR_FILE_DIR, 'maxMODIS.{}.std.nc'.format(year)))


def get_date_nc(prod_type, date, dryrun):
  year = date[0:4]
  doy = '%03d' % int(date[4:])
  prod_dir = get_8day_prod_dir(prod_type)
  if not max_file_exists(prod_type, date):
    logging.info("Creating {} netcdf for {}".format(prod_type, date))
    if not dryrun:
      os.system('./get_date_netcdf.sh {} {} {}'.format(prod_type, year, doy))
      os.system('mv maxMODIS.{}.{}.{}.nc {}'.format(year, doy, prod_type, prod_dir))
  else:
    logging.info("File already exists. Skipping...")


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


def setup_arg_parser():
  parser = argparse.ArgumentParser()
  parser.add_argument('--dryrun', action='store_true')
  return parser

def check_is_only_instance_or_quit():
  name_of_this_script = sys.argv[0].split('/').pop()
  command = "ps -aux | grep %s" % name_of_this_script
  stdout = check_output(command, shell=True)
  lines = stdout.split('\n')
  # Remove empty strings made from the split command
  # Remove entries related to the grep command run as part of the process
  lines = [ line for line in lines if line != '' and 'grep' not in line ]
  if (len(lines) > 1):
    # One entry refers to this instance of the script.
    # More than one entry means there is another instance of the script running.
    logging.info("Another instance of %s is already running. Exiting..." % name_of_this_script)
    sys.exit()

def main():
  os.chdir(MAIN_PATH)
  parser = setup_arg_parser()
  args = parser.parse_args()
  dryrun = args.dryrun
  setup_logging()
  check_is_only_instance_or_quit()
  # Get possible todo days
  todo_dates = get_todo_dates()
  new_stds = []
  for date in todo_dates:
    # Attempt to download std products
    get_date_nc('std', date, dryrun)
    if max_file_exists('std', date):
      new_stds.append(date)
    else:
      logging.info("Fetching NRT file for date {}...".format(date))
      get_date_nc('nrt', date, dryrun)
  if len(new_stds):
    logging.info('Building {} std netcdf'.format(YEAR))
    make_netcdf(YEAR, dryrun)
    # Replace the old std product with the new one
    std_year_f = 'maxMODIS.{}.std.nc'.format(YEAR)
    os.system('mv {} {}'.format(std_year_f, os.path.join(NETCDF_YEAR_FILE_DIR, std_year_f)))


if __name__ == '__main__':
  main()

