
import os, os.path, sys, re, datetime, shutil, traceback, argparse

import xml.etree.ElementTree as ET
import rasterio as rio
import logging as log
from subprocess import check_output
from tempfile import NamedTemporaryFile

from config import *

from util import \
  init_log, \
  try_func, \
  run_subprocess, \
  archive_new_precursors, \
  make_symlinks_for_dates, \
  get_now_est

from state import \
  get_todo_dates_8day_max, \
  get_todo_years_missing_all_year_maxes_precursor, \
  get_three_modis_dates_for_fw2_product, \
  get_todo_dates_fw2_products, \
  delete_nrt_8day_max_files_with_existing_std, \
  delete_symlinks_by_ext, \
  check_is_only_instance_or_quit


def get_cli_args():
  '''Initialize the command-line argument-parser.'''
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--cron', action='store_true', help='Run the full ForWarn 2 task cycle (a normal cron job). No other flags are considered.')
  parser.add_argument('-d', '--datestring', help='TODO Build ForWarn 2 products for a certain date. The argument is of form YYYYDOY, where YYYY is a year and DOY is a day of the year, padded with zeroes if necessary. For example, 2021001 builds the ForWarn 2 product set for day 1 of 2021.')
  parser.add_argument('--email', action='store_true', help='TODO Email the results to addresses in mail_to_addrs.txt')
  parser.add_argument('--dryrun', action='store_true', help='TODO Run this script without actually building any products. Useful for testing.')
  parser.add_argument('--overwrite', action='store_true', help='TODO Overwrite existing products. Use at your own risk!')
  args = parser.parse_args()
  return args


def main():
  check_is_only_instance_or_quit()
  init_log()
  args = get_cli_args()
  if args.cron:
    all_tasks()
    return
  if args.datestring:
    year = datestring[:4]
    jd = datestring[-3:]
    try_func(validate_modis_yr_jd, year, jd, quit_on_fail=True)
    # TODO


def all_tasks():
  '''The main task cycle for ForWarn 2. Builds any missing precursors, updates the graph data files, and builds any missing ForWarn 2 products.'''
  log.info('Starting ForWarn 2 production cycle at {}...'.format(get_now_est()))

  # New precursors
  log.info("Building new 8-day maximum precursors...")
  new_stds = build_all_8day_max_files_for_product_type('std')
  new_nrts = build_all_8day_max_files_for_product_type('nrt')
  if not len(new_stds) and not len(new_nrts):
    log.info("Already up to date!")

  # All-year maxes (graph data)
  log.info("Updating all-year max tifs...")
  years_with_missing_all_year_maxes = get_todo_years_missing_all_year_maxes_precursor()
  years_to_build = [ d['year'] for d in new_stds ]
  years_to_build.extend(years_with_missing_all_year_maxes)
  for year in sorted(set(years_to_build)):
    build_all_year_maxes_tif_for(year)
  if not len(years_to_build):
    log.info("Already up to date!")

  # Cleanup
  archive_new_precursors()
  delete_nrt_8day_max_files_with_existing_std()

  # ForWarn 2 products
  log.info("Building new ForWarn 2 products...")
  fw2_todo_dates = get_todo_dates_fw2_products()
  make_symlinks_for_dates(fw2_todo_dates)
  for d in fw2_todo_dates:
    build_fw2_products_for(d, dryrun=False, email_results=True)
    archive_new_precursors()
  if not len(fw2_todo_dates):
    log.info("Already up to date!")
  log.info('Finished production cycle at {} (EST).'.format(get_now_est()))


def build_fw2_products_for(date, harvest=False, log_path=None, email_results=False, dryrun=False):
  # TODO flesh out this docstring
  '''Build a full set of ForWarn 2 products for some date.
  '''
  year = date['year']
  jd = date['jd']
  log.info("Building ForWarn 2 products for {}/{}...\n".format(year, jd))
  c = [ DODATE_PATH, '{}{}'.format(year, jd) ]
  if not dryrun:
    run_subprocess(c)
  success = False
  # Only move result files for cron runs
  if harvest:
    harvest_products(date, dryrun)
    if fw2_products_exist(date):
      success = True
    else:
      success = False
      logging.error('Something went wrong while trying to move the product files to their destination.')
  if email_results:
    try_func(mail_results, success, d, dryrun, log_path)


def build_all_8day_max_files_for_product_type(product_type):
  '''Build any missing 8-day Aqua/Terra max precursors for a given product type (either std or nrt)'''
  todo = get_todo_dates_8day_max(product_type)
  new_products = []
  if len(todo):
    at_least_one_success = False
    for d in todo:
      exitcode = build_8day_max_for(product_type, d['year'], d['jd'])
      if int(exitcode) == 0:
        at_least_one_success = True
        new_products.append(d)
  return sorted(new_products)


def build_8day_max_for(product_type, year, jd, verbose=False):
  '''Wrapper for build_8day_aqua_terra_max bash script.'''
  c = ['./build_8day_aqua_terra_max', '-t', product_type, '-y', year, '-d', jd]
  if verbose:
    c.append('-v')
  exitcode = run_subprocess(c)
  # wget 404 quits the script with codee 8
  if exitcode == 8:
    log.warn("Tiles are missing upstream, aborting...")
    return exitcode
  return exitcode


def build_all_year_maxes_tif_for(year):
  '''Build a new all-year std maxes tif for a given year.'''
  log.info("Building all-year maxes TIF for {}...".format(year))
  vrt_filename = try_func(
      build_year_maxes_vrt_for_yr,
      year,
      quit_on_fail=True
  )
  tif_filename = 'maxMODIS.{}.std.tif'.format(year)
  new_tif_path_tmp = os.path.join(ALL_YEAR_MAXES_DIR, '{}.tmp'.format(tif_filename))
  # Make the tif
  exitcode = convert_vrt_to_geotiff(vrt_filename, new_tif_path_tmp)
  if int(exitcode) == 0:
    # If we were successful, replace the existing tif with the one we just built
    try:
      os.remove(os.path.join(ALL_YEAR_MAXES_DIR, tif_filename))
    except:
      pass
    os.rename(new_tif_path_tmp, os.path.join(ALL_YEAR_MAXES_DIR, tif_filename))
    log.info('Done building {}'.format(tif_filename))
  else:
    log.error('ERROR: Failed to convert VRT to TIF.')
    try_func(os.remove, new_tif_path_tmp)
  # Remove the VRT file
  try_func(os.remove, vrt_filename)


def build_24day_max_for(year, jd):
  dates = get_three_modis_dates_for_fw2_product(year, jd)
  max_modis_file_template = "maxMODIS.{}.{}.std.img"
  for d in dates:
    jd = d[0]
    year = d[1]
    max_filename = max_modis_file_template.format(year, jd)
    if not os.path.exists(max_filename):
      log.info("Missing {}. Building now...".format(max_filename))
      run_subprocess(["./do_max", year, jd])
  max_modis_max_filename = "maxMODISmax.{}.{}.std.img".format(year, jd)
  os.system("./do_max_max {} {} {} {} {} {}".format(
    dates[0][0], dates[0][1],
    dates[1][0], dates[1][1],
    dates[2][0], dates[2][1]
  ))


########################### HELPERS ###################################


def convert_vrt_to_geotiff(vrt_path, tif_path):
  '''Use gdal_translate to convert a VRT to a GeoTIFF. Used for creating all-year maxes files.
  
  Note: this function invokes gdal_translate with the BIGTIFF=YES creation option.
  '''
  log.info("Converting VRT to TIF: {}".format(vrt_path, tif_path))
  c = [ 'gdal_translate', '-of', 'GTiff', '-co', 'TILED=YES', '-co', 'COMPRESS=DEFLATE', '-co', 'BIGTIFF=YES', vrt_path, tif_path ]
  return run_subprocess(c)


def build_year_maxes_vrt_for_yr(year, **kwargs):
  paths = get_all_year_maxes_vrt_bands_for_yr(year)
  bounds = get_largest_extent_of_datasets(paths)
  big_vrt_name = 'maxMODIS.{}.std.vrt'.format(year)
  log.info("Generating VRT {}...".format(big_vrt_name))
  for i in range(0, len(paths)):
    band_num = str(i+1)
    path = paths[i]
    temp_vrt = build_8day_vrt(path, bounds=bounds)
    if band_num == '1':
      main_tree = ET.parse(temp_vrt)
      main_root = main_tree.getroot()
    else:
      tree = ET.parse(temp_vrt)
      root = tree.getroot()
      bandElement = root.find('VRTRasterBand')
      bandElement.attrib['band'] = band_num
      main_root.append(bandElement)
    os.remove(temp_vrt)
  main_tree.write(big_vrt_name)
  return big_vrt_name


def get_all_year_maxes_vrt_bands_for_yr(year):
  '''Return a list of config dicts for generating an all-year maxes VRT
  for a given year. The result is a VRT with at most 46 bands, where each band
  refers to an 8-day Aqua/Terra maximum in the precursor archive.

  Arguments:
    year: The year to get config for.
    require_all: Throw an exception if a max file is missing for the current year.
  '''
  f_tpl = MAX_8DAY_PRECURSOR_FILENAME_TEMPLATE
  ext = MAX_8DAY_PRECURSOR_FILENAME_EXT
  bands = []
  for jd in ALL_MODIS_JULIAN_DAYS:
    jd_dir = os.path.join(PRECURSORS_DIR, jd)
    f = f_tpl.format(year, jd, 'std', ext)
    path = os.path.join(jd_dir, f)
    if os.path.exists(path):
      p = os.path.join(jd_dir, f)
      bands.append(p)
    else:
      continue
  return bands


def check_same_proj(paths):
  proj_strings = []
  for p in paths:
    with rio.Env():
      with rio.open(p) as src:
        proj_strings.append(src.profile['crs'].to_proj4())
  proj_last = proj_strings[0]
  for proj in proj_strings:
    if proj_last != proj:
      raise TypeError('All datasets must have the exact same projection!')


def get_largest_extent_of_datasets(paths):
  '''Get the maximum value for each extent parameter for a list of rasters.'''
  check_same_proj(paths)
  def max_by_key(iterable, key):
    return max([ getattr(obj, key) for obj in iterable ])
  bounds = []
  for p in paths:
    with rio.Env():
      with rio.open(p) as src:
        bounds.append(src.bounds)
  max_bounds = [ max_by_key(bounds, key) for key in ('left', 'bottom', 'right', 'top') ]
  return max_bounds


def build_8day_vrt(path, bounds=None, vrtnodata=255, band_num=1):
  '''Wrapper for gdalbuildvrt. Build a 1-band VRT..

  Arguments:
    src: path to the source file
    bounds: a python list of the form [ xmin, ymin, xmax, ymax ].
      These values are joined into a string that is passed to the -te flag.
    vrtnodata: Value to use for the -vrtnodata flag.
    band_num: Band number in the source dataset to use.
  '''
  c = [
    'gdalbuildvrt',
    '-vrtnodata', '"{}"'.format(str(vrtnodata)),
    '-b', str(band_num),
    '-overwrite'
  ]
  temp_vrt = '{}.vrt'.format(os.path.basename(path))
  if bounds:
    bounds_string = ' '.join([ str(num) for num in bounds ])
    c.append('-te')
    c.extend(bounds_string.split(' '))
  c.append("{}".format(temp_vrt))
  c.append(path)
  run_subprocess(c)
  return temp_vrt


if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    log.error(traceback.print_exc())
  finally:
    delete_symlinks_by_ext()

