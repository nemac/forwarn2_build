#!/usr/bin/env python3

from util import *

from dkr import run_gdal

from config import *


class ForWarn2Archive:

  def update(self):
    # ForWarn 2 products
    todo_dates = self.get_todo_dates()
    self.make_symlinks_for_dates(todo_dates, dryrun=dryrun)
    success = True
    for d in todo_dates:
      # Add a boolean called 'success' to each dict
      self.build_date(d, archive=True, dryrun=dryrun)
    if not len(todo_dates):
      log.info("Already up to date!")
      os.remove(log_path)
    else:
      log.info('Finished production cycle.')
      mail_results(dates=todo_dates, dryrun=dryrun)

  def build_date(date, archive=False, log_path=None, dryrun=False):
    # TODO flesh out this docstring
    '''Build a full set of ForWarn 2 products for some date.
    '''
    year = date['year']
    jd = date['jd']
    log.info("Building ForWarn 2 products for {}/{}...\n".format(year, jd))
    c = f'{DODATE_PATH} {year}{jd}'
    if not dryrun:
      run_process(c)
    success = False
    if archive:
      self.move(date, dryrun=dryrun)
      if is_ok(date, dryrun=dryrun):
        success = True
      else:
        success = False
        log.error('Something went wrong while trying to move the product files to their destination.')
    date['success'] = success
    return date

  def is_ok(date):
    '''Return True if a full set of products exist for the given date.

    Arguments:
      date_config: dict of the form { 'year': 'YYYY', 'jd': 'DOY' }
    '''
    year = date_config['year']
    jd = date_config['jd']
    date = self.get_datetime_for_year_jd(year, jd)
    file_date = date + datetime.timedelta(days=7)
    datestring = file_date.strftime('%Y%m%d')
    # Keys are directories used by the dodate bash script to place output files
    # Values are the corresponding directory names in the product archive.
    tree = self.get_folder_tree()
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


  def move(date, dryrun=False):
    '''Move new products from the staging directories to the archive.'''
    normal_filename_checks = FW2_NORMAL_DODATE_FILENAME_CHECK.split(',')
    muted_filename_checks = FW2_MUTED_DOATE_FILENAME_CHECK.split(',')
    same_checks = list(filter(lambda d: d in muted_filename_checks, normal_filename_checks))
    if len(same_checks):
      print("Duplicate strings detected for detecting if a file output from dodate is \
        either normal or muted. See FW2_(NORMAL|MUTED)_DODATE_FILENAME_CHECK in .env. \
        Each string should be a comma-separated list of values, with no duplicates across both lists.") 
      sys.exit(1)
    year = date['year']
    jd = date['jd']
    tree = self.get_folder_tree()
    for meta_type in tree.keys():
      dir_maps = tree[meta_type]
      checks = normal_filename_checks if meta_type == 'normal' else muted_filename_checks
      for tmp_dir in dir_maps.keys():
        files = [ f for f in os.listdir(tmp_dir) if year in f and jd in f ]
        meta_type_files = []
        for f in files:
          for s in checks:
            if s in f:
              meta_type_files.append(f) 
        for f in meta_type_files:
          old_fullpath = os.path.join(tmp_dir, f)
          new_filename = self.rename_dodate_filename(f)
          new_fullpath = os.path.join(tree[meta_type][tmp_dir], new_filename)
          log.info("Moving {0}\n to \n{1}\n".format(old_fullpath, new_fullpath, date))
          if not dryrun:
            shutil.copyfile(old_fullpath, new_fullpath)
            # TODO try block?
            os.remove(old_fullpath)

  def get_folder_tree():
    # Assume product directories are nested below the "meta" product type dir
    # (normal or muted/sqrt)
    tree = {
      'normal': {
        FW2_TMP_DIR_1YR: os.path.join(FW2_ARCHIVE_DIR_NORMAL, FW2_PRODUCT_DIR_1YR),
        FW2_TMP_DIR_3YR: os.path.join(FW2_ARCHIVE_DIR_NORMAL, FW2_PRODUCT_DIR_3YR),
        FW2_TMP_DIR_5YR: os.path.join(FW2_ARCHIVE_DIR_NORMAL, FW2_PRODUCT_DIR_5YR),
        FW2_TMP_DIR_ALC: os.path.join(FW2_ARCHIVE_DIR_NORMAL, FW2_PRODUCT_DIR_ALC),
        FW2_TMP_DIR_MEDIAN: os.path.join(FW2_ARCHIVE_DIR_NORMAL, FW2_PRODUCT_DIR_MEDIAN),
        FW2_TMP_DIR_10YR: os.path.join(FW2_ARCHIVE_DIR_NORMAL, FW2_PRODUCT_DIR_10YR),
        FW2_TMP_DIR_PCTPROGRESS: os.path.join(FW2_ARCHIVE_DIR_NORMAL, FW2_PRODUCT_DIR_PCTPROGRESS)
      },
      'muted': {
        FW2_TMP_DIR_1YR: os.path.join(FW2_ARCHIVE_DIR_MUTED, FW2_PRODUCT_DIR_1YR),
        FW2_TMP_DIR_3YR: os.path.join(FW2_ARCHIVE_DIR_MUTED, FW2_PRODUCT_DIR_3YR),
        FW2_TMP_DIR_5YR: os.path.join(FW2_ARCHIVE_DIR_MUTED, FW2_PRODUCT_DIR_5YR),
        FW2_TMP_DIR_ALC: os.path.join(FW2_ARCHIVE_DIR_MUTED, FW2_PRODUCT_DIR_ALC),
        FW2_TMP_DIR_MEDIAN: os.path.join(FW2_ARCHIVE_DIR_MUTED, FW2_PRODUCT_DIR_MEDIAN),
        FW2_TMP_DIR_10YR: os.path.join(FW2_ARCHIVE_DIR_MUTED, FW2_PRODUCT_DIR_10YR),
        # No PCTPROGRESS for muted/sqrt products
      }
    }
    return tree

  def rename_dodate_filename(filename):
    '''Construct the final filename for a ForWarn 2 product file given
    the filename created by the dodate script.'''
    m = re.search("(.*)(\d{4})\.(\d{3})(.*)", filename)
    if m:
      pieces = list(m.groups())
      year = str(pieces[1])
      # Add 7 days to the julian day in the given filename
      jd = str(int(pieces[2]) + 7)
      date = datetime.datetime.strptime('{}{}'.format(year, jd), '%Y%j')
      datestring = date.strftime('%Y%m%d')
      new_pieces = [ pieces[0], datestring, pieces[3] ]
      new_filename = ''.join(new_pieces)
      return new_filename
    else:
      print("Failed to rename filename: {0}".format(filename))

  def get_todo_dates():
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
    this_year_todo_dates = map(lambda jd: self.get_datetime_for_year_jd(today_year, jd), all_days)
    last_year_todo_dates = map(lambda jd: self.get_datetime_for_year_jd(last_year, jd), all_days)
    potential_this_year_todo_dates = self.filter_unavailable_modis_dates(this_year_todo_dates)
    potential_last_year_todo_dates = self.filter_unavailable_modis_dates(last_year_todo_dates)
    potential_todo_dates = potential_this_year_todo_dates + potential_last_year_todo_dates
    potential_todo_date_dicts = list(map(self.get_year_jd_config_for_datetime, potential_todo_dates))
    todo_dates = list(filter(lambda d: not is_ok(d), potential_todo_date_dicts))
    return todo_dates

  def get_datetime_for_year_jd(year, jd):
    '''Return a datetime object for a date given a year and day of the year.'''
    return datetime.datetime.strptime('{}{}'.format(year, jd), '%Y%j')

  def get_year_jd_config_for_datetime(date):
    '''Given a datetime object, return a dictionary of the form
    { 'year': 'YYYY', 'jd': 'JJJ' } where JJJ is a zero-padded day of the year.
    '''
    return { 'year': date.strftime('%Y'), 'jd': date.strftime('%j') }

  def filter_unavailable_modis_dates(dates):
    '''Given a list of MODIS product dates, remove any dates that are
    either in the future, or are simply too near the present for products
    to be available yet (at most 8 days in the past from the current day).'''
    day_delta = 8
    today = datetime.datetime.today()
    return list(filter(lambda d: d <= today - datetime.timedelta(days=day_delta), dates))

  def get_three_dates(year, jd):
    '''Given the year and julian day for an 8-day MODIS product, return a list of 
    three MODIS product dates: the supplied date first, followed by the previous two
    MODIS dates. These three dates represent the three 8-day MODIS cycles that
    form the basis of a 24-day ForWarn 2 cycle.

    The dates returned are repreesented as dictionaries with two keys: 'year' and 'jd'.
    '''
    all_jds = ALL_MODIS_JULIAN_DAYS
    dates = list(map(lambda d: { 'jd': d, 'year':  year }, all_jds))
    if jd == '009':
      dates[2] = { 'jd' : '361', 'year' : str(int(year)-1) }
    if jd == '001':
      dates[1] = { 'jd' : '361', 'year' : str(int(year)-1) }
      dates[2] = { 'jd' : '353', 'year' : str(int(year)-1) }
    return dates

  def make_symlinks_for_dates(dates, dryrun=False):
    '''Make symbolic links in the current directory to any precursors that may be useful for creating ForWarn 2 products for the given dates.

    dates: a list of dicts, each with two keys, 'year' and 'jd'
    '''
    jds = []
    for d in dates:
      year = d['year']
      jd = d['jd']
      jd_dir = os.path.join(PRECURSORS_DIR, jd)
      three_jds = [ d['jd'] for d in self.get_three_dates(year, jd) ]
      jds.extend(three_jds)
    jds = sorted(set(jds))
    for jd in jds:
      self.link_by_pattern(PRECURSORS_DIR, '.', ".*\d{4}\."+jd+".*\.img", dryrun=dryrun) 

  def link_by_pattern(source_dir, dest_dir, pattern, dryrun=False):
    '''Recursively walk source_dir and make a symlink in dest_dir for every file found if the file matches the supplied regex pattern.'''
    log.debug(f"Making symlinks for all files found here:\n{source_dir}into...\n{dest_dir}\nthat match this pattern: {pattern}")
    found_at_least_one_match = False
    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            m = re.search(pattern, filename)
            if m:
                found_at_least_one_match = True
                src = os.path.abspath(os.path.join(root, filename))
                dst = os.path.abspath(os.path.join(dest_dir, filename))
                try:
                  if not dryrun:
                    os.symlink(src, dst)
                except:
                  pass
            else:
                pass
    if not found_at_least_one_match:
      log.warn("No files found to make symbolic links for!")

