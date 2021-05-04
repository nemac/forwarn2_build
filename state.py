
from subprocess import Popen, PIPE, STDOUT, check_output
import os, os.path, sys, re, traceback, shutil, datetime
import logging as log

from util import *


############################# CHANGE STATE ##############################################


def delete_symlinks_by_ext(ext='.img'):
  '''Delete any symlinks in the current directory that have a certain file extension (default is '.img')'''
  log.debug("Cleaning up environment...".format(ext))
  for f in os.listdir('.'):
    if os.path.islink(f) and f.endswith(ext) and not os.path.isdir(f):
      os.remove(f) 


def delete_nrt_8day_max_files_with_existing_std(dryrun=False):
  # TODO this is not working
  '''Removes all NRT 8-day max files if an STD file already exists for the same period.'''
  jds = ALL_MODIS_JULIAN_DAYS
  found_at_least_one_nrt_to_remove = False
  for jd in jds:
    f_tpl = 'maxMODIS.{}.{}.{}.img'
    folder = os.path.join(PRECURSORS_DIR, jd)
    for year in get_all_modis_data_years():
      std_path = os.path.join(folder, f_tpl.format(year, jd, 'std'))
      nrt_path = os.path.join(folder, f_tpl.format(year, jd, 'nrt'))
      if os.path.exists(std_path) and os.path.exists(nrt_path):
        found_at_least_one_nrt_to_remove = True
        log.info("Deleting {} (std version already exists)...".format(nrt_path))
        if not dryrun:
          try_func(os.remove, nrt_path)


def check_is_only_instance_or_quit():
  name_of_this_script = sys.argv[0].split('/').pop()
  command = "ps -aux | grep %s" % name_of_this_script
  stdout = str(check_output(command, shell=True))
  lines = stdout.split('\n')
  # Remove empty strings made from the split command
  # Remove entries related to the grep command run as part of the process
  lines = [ line for line in lines if line != '' and 'grep' not in line ]
  if (len(lines) > 1):
    # One entry refers to this instance of the script.
    # More than one entry means there is another instance of the script running.
    print("Another instance of {} is already running! Or it's open in a text editor (LOL). Exiting...".format(name_of_this_script))
    sys.exit() 


############################# GET STATE ##############################################


def get_todo_dates_fw2_products():
  '''Get a list of potential dates for which ForWarn 2 products may be built.

  Return a list of MODIS product dates in the past two years for which:

  1. Enough time has passed that NRT data for that date may be available.
  2. A complete set of ForWarn 2 products does not exist.

  In theory NRT data should be available for these dates, but it's possible the data is late.
  '''
  all_days = ALL_FW2_JULIAN_DAYS
  today = datetime.datetime.today()
  today_year = today.strftime('%Y')
  last_year = str(int(today_year) - 1)
  this_year_todo_dates = map(lambda jd: get_datetime_for_year_jd(today_year, jd), all_days)
  last_year_todo_dates = map(lambda jd: get_datetime_for_year_jd(last_year, jd), all_days)
  potential_this_year_todo_dates = filter_unavailable_modis_dates(this_year_todo_dates)
  potential_last_year_todo_dates = filter_unavailable_modis_dates(last_year_todo_dates)
  potential_todo_dates = potential_this_year_todo_dates + potential_last_year_todo_dates
  potential_todo_date_dicts = list(map(get_year_jd_config_for_datetime, potential_todo_dates))
  todo_dates = list(filter(lambda d: not fw2_products_exist(d), potential_todo_date_dicts))
  return todo_dates


def get_todo_dates_8day_max(product_type, include_all_std_years=True, exclude_nrt_if_std_exists=True):
  '''Get a list of MODIS product dates for which a corresponding
  Aqua/Terra maximum precursor is missing.

  Arguments:
    product_type: Either 'nrt' or 'std'
    include_all_std_years: Set to True to consider all years (2003-present) 
      when determining missing STD max products.
      Only valid if product_type is 'std'.
    exclude_nrt_if_std_exists: Set to True to exclude potential NRT product days 
      if std data is available locally. True by default. Only valid if
      product_type is 'nrt'.
  '''
  days = ALL_MODIS_JULIAN_DAYS
  today = datetime.datetime.today()
  this_year = today.strftime('%Y')
  all_years = get_all_modis_data_years() 
  dates = []
  if include_all_std_years and product_type == 'std':
    for yr in all_years:
      year_dates = map(lambda day: get_datetime_for_yr_jd(yr, day), days)
      dates.extend(year_dates)
  else:
    dates = map(lambda day: get_datetime_for_yr_jd(this_year, day), days)
  valid_dates = filter_unavailable_modis_dates(dates)
  converted_dates = [ { 'year': d.strftime('%Y'), 'jd': d.strftime('%j') } for d in valid_dates ]
  todo_days = filter(lambda d: not modis_8day_max_file_exists(d['year'], d['jd'], product_type), converted_dates )
  # Exclude nrt from todo if the equivalent std product already exists (default)
  if exclude_nrt_if_std_exists and product_type == 'nrt':
    todo_days = filter(lambda d: not modis_8day_max_file_exists(d['year'], d['jd'], 'std'), todo_days)
  return list(todo_days)


def modis_8day_max_file_exists(year, jd, product_type, ext='img', verbose=False):
  tpl = MAX_8DAY_PRECURSOR_FILENAME_TEMPLATE
  f = tpl.format(year, jd, product_type, ext)
  path = get_precursor_path(jd, f)
  if os.path.exists(path):
    if verbose:
      log.info("Found {}".format(path))
    return True
  else:
    return False


def get_todo_years_missing_all_year_maxes_precursor():
  '''Returns a list of years (strings) with missing all-year maxes tifs'''
  tpl = ALL_YEAR_MAXES_PRECURSOR_FILENAME_TEMPLATE
  ext = ALL_YEAR_MAXES_PRECURSOR_FILE_EXT
  all_years = get_all_modis_data_years()
  return list(filter(lambda y: not os.path.exists(os.path.join(ALL_YEAR_MAXES_DIR, tpl.format(y, ext))), all_years))


def filter_unavailable_modis_dates(dates):
  '''Given a list of MODIS product dates, remove any dates that are
  either in the future, or are simply too near the present for products
  to be available yet (at most 8 days in the past from the current day).'''
  day_delta = 8
  today = datetime.datetime.today()
  return list(filter(lambda d: d <= today - datetime.timedelta(days=day_delta), dates))


def fw2_products_exist(date_config, dryrun=False):
  '''Return True if a full set of products exist for the given date.

  Arguments:
    date_config: dict of the form { 'year': 'YYYY', 'jd': 'DOY' }
  '''
  year = date_config['year']
  jd = date_config['jd']
  date = get_datetime_for_year_jd(year, jd)
  file_date = date + datetime.timedelta(days=7)
  datestring = file_date.strftime('%Y%m%d')
  # Keys are directories used by the dodate bash script to place output files
  # Values are the corresponding directory names in the product archive.
  tree = get_fw2_archive_tree()
  all_products_exist = True
  for source in tree.keys():
    source_dir = FW2_ARCHIVE_DIR_NORMAL if source == 'normal' else FW2_ARCHIVE_DIR_MUTED
    for dodate_dir in tree[source].keys():
      dir_path = tree[source][dodate_dir]
      if not os.path.exists(dir_path):
        log.error("Missing product directory {}!".format(dir_path))
      files = os.listdir(dir_path)
      files = list(filter(lambda f: datestring in f, files))
      if not len(files):
        log.debug("Unable to find file in archive for {} {} {}".format(source_dir, dodate_dir, datestring))
        all_products_exist = False
  if not all_products_exist:
    log.warn("Missing ForWarn 2 products in the archive for {}/{}...".format(year, jd))
  if dryrun:
    return True
  return all_products_exist


def remove_staging_files(dryrun=False):
  '''Remove the files Aqua.img and Terra.img from the staging environment.'''
  files = [ 'Aqua.img', 'Terra.img' ]
  for f in files:
    if os.path.exists(f):
      log.info("Removing staging file {}".format(f))
      try: os.remove(f)
      except:
        log.error("Unable to remove staging file {}".format(f))


def get_all_modis_data_years():
  '''Return a list of years (strings) for which MODIS data is available on the GIMMS server.'''
  start = int(MODIS_DATA_YEAR_START)
  today = datetime.datetime.today()
  this_year = today.strftime('%Y')
  all_years = list(range(start, int(this_year)+1 ))
  return [ str(y) for y in all_years ]


