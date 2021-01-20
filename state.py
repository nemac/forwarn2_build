
from subprocess import Popen, PIPE, STDOUT
import os, os.path, sys, re, traceback, shutil, datetime
import logging as log



############################# STATE HELPERS ##############################################


def get_todo_dates_fw2_products():
  '''Returns a list of MODIS product dates in the past two years for which:

  1. Enough time has passed that NRT data for that date may be available..
  2. A complete set of ForWarn 2 products does not exist.
  '''
  all_days = ALL_MODIS_JULIAN_DAYS
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


def delete_nrt_8day_max_files_with_existing_std():
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
        log.info("Deleting {} (STD exists)...".format(nrt_path))
        try_func(os.remove, nrt_path)


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


def fw2_products_exist(date_config):
  year = date_config['year']
  jd = date_config['jd']
  date = get_datetime_for_year_jd(year, jd)
  file_date = date + datetime.timedelta(days=7)
  datestring = date.strftime('%Y%m%d')
  
  for source in SOURCE_DIRS:
    for key in PRODUCT_DIRS:
      prod_dir = PRODUCT_DIRS[key]
      path = os.path.join('.', source, prod_dir)
      # There is no square root % progress product, so skip this combination
      if not os.path.exists(path) or (source == 'ForWarn2_Sqrt' and key == 'pctprogress'):
        continue
      files = os.listdir(path)
      files = list(filter(lambda f: datestring in f, files))
      if not len(files):
        return False
  return True


