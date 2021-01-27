import smtplib
from email.message import EmailMessage

from subprocess import Popen, PIPE, STDOUT
import os, os.path, sys, re, traceback, shutil, datetime
from pytz import timezone

from tempfile import NamedTemporaryFile
import base64
import logging as log

# Some helpful constants

ALL_MODIS_JULIAN_DAYS = ("001", "009", "017", "025", "033", "041", "049", "057", "065", "073", "081", "089", "097", "105", "113", "121", "129", "137", "145", "153", "161", "169", "177", "185", "193", "201", "209", "217", "225", "233", "241", "249", "257", "265", "273", "281", "289", "297", "305", "313", "321", "329", "337", "345", "353", "361")

# ForWarn 2 julian days are the same as MODIS, except we exclude day 361
# However, we still build precursors for day 361 since it's used when calculating
# products for days 001 and 009.
ALL_FW2_JULIAN_DAYS=ALL_MODIS_JULIAN_DAYS[:-1]

# Each tuple is a triplet of MODIS product days corresponding to
# a ForWarn 2 product window for the first day in the tuple.
INTERVALS = [ ("361","353","345"), ("353","345","337"), ("345","337","329"), ("337","329","321"), ("329","321","313"), ("321","313","305"), ("313","305","297"), ("305","297","289"), ("297","289","281"), ("289","281","273"), ("281","273","265"), ("273","265","257"), ("265","257","249"), ("257","249","241"), ("249","241","233"), ("241","233","225"), ("233","225","217"), ("225","217","209"), ("217","209","201"), ("209","201","193"), ("201","193","185"), ("193","185","177"), ("185","177","169"), ("177","169","161"), ("169","161","153"), ("161","153","145"), ("153","145","137"), ("145","137","129"), ("137","129","121"), ("129","121","113"), ("121","113","105"), ("113","105","097"), ("105","097","089"), ("097","089","081"), ("089","081","073"), ("081","073","065"), ("073","065","057"), ("065","057","049"), ("057","049","041"), ("049","041","033"), ("041","033","025"), ("033","025","017"), ("025","017","009"), ("017","009","001"), ("009","001","361"), ("001","361","353") ]


def load_env(ns=globals()):
  '''Load the variables defined in .env into the globals dictionary.'''
  with open('.env') as f:
    lines = [ line.strip() for line in f.readlines() ]
    lines = filter(lambda line: '=' in line and not line.startswith('#'), lines)
    env = [ line.split('=') for line in lines ]
    for arr in env:
      key = arr[0]
      val = ''.join(arr[1:])
      ns[key] = val


# Load the environment variables into the globals dict
load_env()



########################## LOG HELPERS ####################################


def init_log(level=log.DEBUG, log_path=None, dryrun=False):
  '''Initialize logging.''' 
  logger = log.getLogger()
  for handler in logger.handlers:
    logger.removeHandler(handler)
  if dryrun:
    formatter_string = '[%(asctime)s EST] [DRYRUN] [%(levelname)s] %(message)s'
  else:
    formatter_string = '[%(asctime)s] [%(levelname)s] %(message)s'
  formatter = log.Formatter(formatter_string)
  file_handler = log.FileHandler(filename=log_path, mode='a')
  stream_handler = log.StreamHandler()
  logger.addHandler(file_handler)
  logger.addHandler(stream_handler)
  for handler in logger.handlers[:]:
    handler.setFormatter(formatter)
  logger.setLevel(level)


def get_default_log_path():
  now = get_now_est(time_format=LOG_FILE_TIMESTAMP_FORMAT)
  log_path = LOG_PATH_TEMPLATE.format(now)
  return log_path


def get_now_est(formatted=True, time_format='%Y-%m-%d %I:%M:%S%p', tz='US/Eastern'):
  '''Do you have the time?'''
  now = datetime.datetime.now(timezone(tz)) 
  if formatted:
    return now.strftime(time_format)
  else:
    return now


def get_log_path(logger=None):
  if not logger:
    logger = log.getLogger()
  paths = [ handler.baseFilename for handler in logger.handlers if isinstance(handler, log.FileHandler) ]
  if len(paths) > 1:
    log.error("This logger has two file handlers associated with it. That's bad, right?")
  if not len(paths):
    return None
  if len(paths) == 1:
    return paths[0]


# TODO
def mail_results(dates=[], dryrun=False):
  if not os.path.exists(MAIL_TO_ADDRS_FILE):
    log.error("Unable to email results since mail_to_addrs.txt is missing.")
  mail_to_addrs = []
  try:
    with open(MAIL_TO_ADDRS_FILE) as f:
      for addr in f:
        mail_to_addrs.append(addr.strip())
      if not len(mail_to_addrs):
        raise OSError("File is empty: {}".format(MAIL_TO_ADDRS_FILE))
      for addr in mail_to_addrs:
        if '@' not in addr:
          raise ValueError("Malformed email address in {}: {}".format(MAIL_TO_ADDRS_FILE, addr))
  except FileNotFoundError as e:
    log.error("File is missing: {}".format(MAIL_TO_ADDRS_FILE))
    log.error("See MAIL_TO_ADDRS in .env.".format(MAIL_TO_ADDRS_FILE))
    sys.exit(1)
  except OSError as e:
    log.error(e.__str__())
    sys.exit(1)
  except ValueError as e:
    log.error(e.__str__())
  dryrun_subject_text = '[DRYRUN] ' if dryrun else ''
  total_success = len([ d for d in dates if d['success'] ]) == len(dates)
  if len(dates):
    date_list_str = ', '.join([ '{}/{}'.format(d['year'], d['jd']) for d in dates ])
    date_list_str = ' (' + date_list_str +  ')'
  else:
    date_list_str = ''
  if total_success:
    subject_text = "{}FW2 Product Generation{}".format(dryrun_subject_text, date_list_str).rstrip()
    body_text = "Success! See attached log for details."
  else:
    subject_text = "{}FAILED: FW2 Product Generation{}".format(dryrun_subject_text, date_list_str).rstrip()
    body_text = "Something went wrong... Usually this just means the most recent NRT tiles are missing from the GIMMS server. We'll try again in a bit."
  body_text += "\n\n"
  if len(dates):
    body_text += "Summary of FW2 Products:\n\n"
  for d in dates:
    status_text = "OK" if d['success'] else "FAILED"
    body_text += "Product: {} / {}\n".format(d['year'], d['jd'])
    body_text += "Status: {}\n".format("OK" if d['success'] else "FAILED")
    body_text += "\n"
  log_path = get_log_path()
  if log_path:
    with open(log_path) as f:
      log_contents = f.read()
  else:
    log_contents = "Log file is missing!"
  log.info("Emailing results to {}".format(', '.join(mail_to_addrs)))
  msg = EmailMessage()
  msg['Subject'] = subject_text
  msg['From'] = EMAIL_FROM_ADDRESS
  msg['To'] = ', '.join(mail_to_addrs)
  msg.set_content(body_text)
  msg.add_attachment(log_contents, filename=os.path.basename(log_path))
  s = smtplib.SMTP('localhost', 25)
  s.send_message(msg)
  s.quit()


########################## CONTROL HELPERS ####################################


def run_subprocess(command, dryrun=False):
  '''Runs a subprocess and logs stdout and stderr to log.debug.'''
  try:
    log.debug('Starting subprocess: {}'.format(' '.join(command)))
    if not dryrun:
      process = Popen(command, stdout=PIPE, stderr=STDOUT)
      with process.stdout:
        for line in iter(process.stdout.readline, b''):
          log.debug('[SUBPROCESS] {}'.format(line.rstrip().decode("utf-8")))
      exitcode = process.wait()
    else:
      exitcode = 0  
    if int(exitcode) == 0:
      log.debug('Subprocess completed successfully.')
    else:
      log.warn('Subprocess exited with non-zero status code {}'.format(str(exitcode)))
    return exitcode
  except Exception as e:
    log.error(traceback.print_exc())
    log.error(e)
    return 1


# TODO this function kind of sucks...
def try_func(f, *args, **kwargs):
  '''Run a function in a try block, logging any resulting error
  and exiting the program is directed.

  All positional and keyword arguments will be passed as arguments
  to the supplied function.

  There are two optional keyword arguments that affect this function:
    log_error: Log errors. Default is True.
    quit_on_fail: Invoke sys.exit(1) if an exception is caught.
  '''
  try:
    result = f(*args, **kwargs)
    return result
  except:
    if kwargs.get('log_error', True):
      log.error(traceback.print_exc())
    if kwargs.get('quit_on_fail', False):
      log.info("Exiting due to unrecoverable error...")
      sys.exit(1)



################################# DATE HELPERS #################################


def get_year_jd_config_for_datetime(date):
  '''Given a datetime object, return a dictionary of the form
  { 'year': 'YYYY', 'jd': 'JJJ' } where JJJ is a zero-padded day of the year.
  '''
  return { 'year': date.strftime('%Y'), 'jd': date.strftime('%j') }


def validate_modis_yr_jd(year, jd):
  '''Throw an exception if a given year or julian day is invalid.'''
  today_year = datetime.datetime.today().strftime('%Y')
  if int(year) < int(MODIS_DATA_YEAR_START) or int(year) > int(today_year):
    raise ValueError('Bad year given. Must be a four-digit number in the range {}-{}.'.format(MODIS_DATA_YEAR_START, today_year))
  if str(jd) not in ALL_MODIS_JULIAN_DAYS:
    raise ValueError('Bad julian day given. Must be one of: {}'.format(', '.join(ALL_MODIS_JULIAN_DAYS)))


def get_datetime_for_year_jd(year, jd):
  '''Return a datetime object for a date given a year and day of the year.'''
  return datetime.datetime.strptime('{}{}'.format(year, jd), '%Y%j')


def get_datetime_for_yr_jd(year, jd):
  '''Return a datetime given a year and a (zero-padded) day of the year.'''
  validate_modis_yr_jd(year, jd)
  today_year = datetime.datetime.today().strftime('%Y')
  date = datetime.datetime.strptime('{}{}'.format(str(year), jd), '%Y%j')
  return date


def get_three_modis_dates_for_fw2_product(year, jd):
  '''Given the year and julian day for an 8-day MODIS product, return a list of 
  three MODIS product dates: the supplied date first, followed by the previous two
  MODIS dates. These three dates represent the three 8-day MODIS cycles that
  form the basis of a 24-day ForWarn 2 cycle.

  The dates returned are repreesented as dictionaries with two keys: 'year' and 'jd'.
  '''
  validate_modis_yr_jd(year, jd)
  all_jds = ALL_MODIS_JULIAN_DAYS
  dates = list(map(lambda d: { 'jd': d, 'year':  year }, all_jds))
  if jd == '009':
    dates[2] = { 'jd' : '361', 'year' : str(int(year)-1) }
  if jd == '001':
    dates[1] = { 'jd' : '361', 'year' : str(int(year)-1) }
    dates[2] = { 'jd' : '353', 'year' : str(int(year)-1) }
  return dates




############################## FILE HELPERS ########################################


def get_fw2_archive_tree():
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


def harvest_products(date, dryrun=False):
  normal_filename_checks = FW2_NORMAL_DODATE_FILENAME_CHECK.split(',')
  muted_filename_checks = FW2_MUTED_DOATE_FILENAME_CHECK.split(',')
  same_checks = list(filter(lambda d: d in muted_filename_checks, normal_filename_checks))
  if len(same_checks):
    log.error("Duplicate strings detected for detecting if a file output from dodate is \
      either normal or muted. See FW2_(NORMAL|MUTED)_DODATE_FILENAME_CHECK in .env. \
      Each string should be a comma-separated list of values, with no duplicates across both lists.") 
    sys.exit(1)
  year = date['year']
  jd = date['jd']
  tree = get_fw2_archive_tree()
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
        new_filename = rename_dodate_filename(f)
        new_fullpath = os.path.join(tree[meta_type][tmp_dir], new_filename)
        log.info("Moving {0}\n to \n{1}\n".format(old_fullpath, new_fullpath, date))
        if not dryrun:
          shutil.copyfile(old_fullpath, new_fullpath)
          try_func(os.remove, old_fullpath)


def get_8day_max_filename(year, jd, product_type, ext='img'):
  '''Get the filename for an 8-day Aqua/Terra maximum precursor given
  a year, julian day, product type (either 'nrt' or 'std'), and file extension.'''
  tpl = MAX_8DAY_PRECURSOR_FILENAME_TEMPLATE
  f = tpl.format(year, jd, product_type, ext)
  return f


def get_all_year_std_maxes_filename(year, ext='tif'):
  '''Get the filename for an all-year Aqua/Terra maxes filename given
  a year and a file extension.'''
  tpl = ALL_YEAR_MAXES_PRECURSOR_FILENAME_TEMPLATE
  f = tpl.format(year, ext)
  return f


def get_precursor_path(jd, filename):
  '''Get the path to a file in the precursor archive.'''
  return os.path.join(PRECURSORS_DIR, jd, filename)


def make_symlinks_for_dates(dates, dryrun=False):
  '''Make symbolic links in the current directory to any precursors that may be useful for creating ForWarn 2 products for the given dates.

  dates: a list of dicts, each with two keys, 'year' and 'jd'
  '''
  jds = []
  for d in dates:
    year = d['year']
    jd = d['jd']
    jd_dir = os.path.join(PRECURSORS_DIR, jd)
    three_jds = [ d['jd'] for d in get_three_modis_dates_for_fw2_product(year, jd) ]
    jds.extend(three_jds)
  jds = sorted(set(jds))
  for jd in jds:
    build_symlinks_by_pattern(PRECURSORS_DIR, '.', ".*\d{4}\."+jd+".*\.img", dryrun=dryrun) 



def build_symlinks_by_pattern(source_dir, dest_dir, pattern, dryrun=False):
  '''Recursively walk source_dir and make a symlink in dest_dir for every file found if the file matches the supplied pattern.'''
  log.debug("Making symlinks for all files found in {} into {} that match this pattern: {}".format(source_dir, dest_dir, pattern))
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


def archive_new_precursors(base_dir='.', ext='.img', dryrun=False):
  '''Move any precursor files (hard links) in the current directory to the precursor archive.'''
  all_jds = ALL_MODIS_JULIAN_DAYS
  files = os.listdir(base_dir)
  for f in files:
    if f.endswith(ext) and not os.path.islink(f):
      for jd in all_jds:
        if re.search(".*\d{4}\."+jd+".*"+ext+"$", f):
          new_path = os.path.join(PRECURSORS_DIR, jd, f)
          log.info("Moving new precursor {} to the precursor archive...".format(f))
          if not dryrun:
            shutil.move(f, new_path)


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
    log.error("Failed to rename filename: {0}".format(filename))


