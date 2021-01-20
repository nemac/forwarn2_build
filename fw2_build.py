
import logging as log
import rasterio as rio
import os, os.path, sys, re, datetime, shutil
import xml.etree.ElementTree as ET
import argparse

from subprocess import check_output
from tempfile import NamedTemporaryFile

from config import *
from state import get_todo_dates_8day_max
from util import *


def build_fw2_products_for(date, dryrun=False, is_cli_run=False, log_path=None, email_results=False):
  #TODO flesh out this docstring
  # TODO refactor is_cli_run
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
  if not is_cli_run:
    harvest_products(date, dryrun)
    if fw2_products_exist(date):
      success = True
    else:
      success = False
      logging.error('Something went wrong while trying to move the product files to their destination.')
  else:
    # We're doing a CLI run for a specific date.
    # Defaulting to true for now
    success = True
  if email_results:
    try_func(mail_results, success, d, dryrun, log_path)


def build_all_8day_max_files_for_product_type(product_type):
  '''Build any missing 8-day Aqua/Terra max precursors for a given product type (either std or grt)'''
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
  # TODO support verbosity
  '''Wrapper for build_8day_aqua_terra_max bash script.'''
  log.info("Attempting to build MODIS {} Aqua/Terra max raster for {}/{}...".format(product_type, year, jd))
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
      # arguments to build_year_maxes_vrt_for_yr
      '1', '255', None, year, 
      # arguments to try_func
      quit_on_fail=True,
      fail_log='Failed to build VRT for {} std all-year maxes.'.format(year)
  )
  tif_filename = 'maxMODIS.{}.std.tif'.format(year)
  new_tif_path_tmp = os.path.join(ALL_YEAR_MAXES_DIR, '{}.tmp'.format(tif_filename))
  # Make the tif
  exitcode = convert_vrt_to_geotiff(vrt_filename, new_tif_path_tmp)
  if int(exitcode) == 0:
    # If we were successful, replace the existing tif with the one we just built
    try_func(os.remove, os.path.join(ALL_YEAR_MAXES_DIR, tif_filename))
    os.rename(new_tif_path_tmp, os.path.join(ALL_YEAR_MAXES_DIR, tif_filename))
    log.info('Done building {}'.format(tif_filename))
  else:
    log.error('ERROR: Failed to convert VRT to TIF.')
    try_func(os.remove, new_tif_path_tmp)
  # Remove the VRT file
  try_func(os.remove, vrt_filename)


def convert_vrt_to_geotiff(vrt_path, tif_path):
  '''Use gdal_translate to convert a VRT to a GeoTIFF. Used for creating all-year maxes files.
  
  Note: this function invokes gdal_translate with the BIGTIFF=YES creation option.
  '''
  log.info("Converting VRT to TIF: {}}".format(vrt_path, tif_path))
  c = [ 'gdal_translate', '-of', 'GTiff', '-co', 'TILED=YES', '-co', 'COMPRESS=DEFLATE', '-co', 'BIGTIFF=YES', vrt_path, tif_path ]
  return run_subprocess(c)


def get_vrt_config_by_yr(year, quit_if_missing_files=False, verbose=False):
  precursors_dir = './precursors'
  days = get_all_todo_days()
  f_tpl = 'maxMODIS.{}.{}.std.img'
  config = []
  found_missing = False
  for jd in days:
    jd_dir = os.path.join(precursors_dir, jd)
    f = f_tpl.format(year, jd)
    path = os.path.join(jd_dir, f)
    if os.path.exists(path):
      c = { 'name': 'maxMODIS_{}_{}'.format(year, jd), 'path': os.path.join(jd_dir, f) }
      config.append(c)
    else:
      found_missing = True
      if verbose:
        log.warn("Missing file {}".format(f))
  if found_missing and quit_if_missing_files:
    sys.exit()
  return config


def build_year_maxes_vrt_for_yr(b, vrtnodata, dir_path, year):
  bands_config = get_vrt_config_by_yr(year)
  check_same_proj(bands_config, dir_path)
  bounds = get_largest_extent_of_datasets(bands_config, dir_path)
  big_vrt_name = 'maxMODIS.{}.std.vrt'.format(year)
  log.info("Generating VRT {}...".format(big_vrt_name))
  for i in range(0, len(bands_config)):
    band_num = str(i+1)
    band_config = bands_config[i]
    temp_vrt = build_intermediate_vrt(band_config, bounds, b, vrtnodata, dir_path)
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


def check_same_proj(bands_config, dir_path):
  paths = [ os.path.join(c, dir_path) for c in bands_config ]
  proj_strings = []
  for p in paths:
    with rio.Env():
      with rio.open(p) as src:
        proj_strings.append(src.profile['crs'].to_proj4())
  proj_last = proj_strings[0]
  for proj in proj_strings:
    if proj_last != proj:
      raise TypeError('All datasets must have the exact same projection!')


def get_largest_extent_of_datasets(bands_config, dir_path):
  def max_by_key(iterable, key):
    return max([ getattr(obj, key) for obj in iterable ])
  paths = [ os.path.join(c, dir_path) for c in bands_config ]
  bounds = []
  for p in paths:
    with rio.Env():
      with rio.open(p) as src:
        bounds.append(src.bounds)
  max_bounds = [ max_by_key(bounds, key) for key in ('left', 'bottom', 'right', 'top') ]
  return max_bounds


def build_intermediate_vrt(band_config, bounds, b, vrtnodata, dir_path):
  c = [
    'gdalbuildvrt',
    '-vrtnodata', '"{}"'.format(vrtnodata),
    '-b', b,
    '-overwrite'
  ]
  dataset_path = os.path.join(band_config, dir_path)
  temp_vrt = '{0}.vrt'.format(os.path.join('./', band_config['name']))
  bounds_string = ' '.join([ str(num) for num in bounds ])
  c.append('-te')
  c.extend(bounds_string.split(' '))
  c.append("{0}".format(temp_vrt))
  c.append(dataset_path)
  run_process(c)
  return temp_vrt


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

