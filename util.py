
from subprocess import Popen, PIPE, STDOUT
import os, os.path, sys, re, traceback, shutil, datetime
import logging as log

from config import *


def mail_results(success, date, dryrun, log_path):
  jd = date['jd']
  mail_to_addrs = []
  with open(MAIL_TO_ADDRS_FILE) as f:
    for addr in f:
      mail_to_addrs.append(addr.strip())
  logging.info("Emailing results to: {0}".format(' '.join(mail_to_addrs)))
  dryrun_body_text = "" if not dryrun else "NOTE: THIS IS A TEST OF THE FORWARN 2 SYSTEM!\n\n"
  if success:
    subject_text = "FW2 Day {0} Product Generation".format(day).rstrip()
    body_text = "{0}Success! The log is attached to this email.".format(dryrun_body_text)
  else:
    subject_text = "FAILED: FW2 Day Product Generation {0}".format(day).rstrip()
    body_text = "{0}Looks like something went wrong. We'll try again and send another notification email.".format(dryrun_body_text)
  # Read the log file and encode as base64
  with open(log_path) as f:
    log_contents = f.read()
  jog_encoded = log_contents.encode('base64')
  # Load the email template file
  with open(EMAIL_TEMPLATE_FILE) as f:
    template_contents = f.read()
  # Replace the placeholder text with subject, content, log filename, and encoded attachment text
  log_filename = os.path.split(log_path)[1]
  rendered_email = template_contents.replace('EMAIL_SUBJECT_REPLACE', subject_text)
  rendered_email = rendered_email.replace('EMAIL_BODY_REPLACE', body_text)
  rendered_email = rendered_email.replace('LOG_FILENAME_REPLACE', log_filename)
  rendered_email = rendered_email.replace('ATTACHMENT_CONTENT_REPLACE', log_encoded)
  # Make a temporary file with the contents of the email
  f = NamedTemporaryFile(delete=False)
  f.write(rendered_email)
  filename = f.name
  f.close()
  # Must use full path to sendmail for cron jobs. (Cron is not aware of normal environment variables like $PATH)
  mail_command = "/usr/sbin/sendmail -f nemacmailer@gmail.com {0} < {1}".format(' '.join(mail_to_addrs), filename)

  # Send the email to each recipient in mail_to_addrs
  exit_status = os.system(mail_command)
  os.remove(filename)


########################## CONTROL HELPERS ####################################


def run_subprocess(command):
  '''Runs a subprocess and logs stdout and stderr to log.debug.'''
  try:
    log.debug('Starting subprocess: {}'.format(' '.join(command)))
    process = Popen(command, stdout=PIPE, stderr=STDOUT)
    with process.stdout:
      for line in iter(process.stdout.readline, b''):
        log.debug('    {}'.format(line.rstrip().decode("utf-8")))
    exitcode = process.wait()
    if int(exitcode) == 0:
      log.debug('Subprocess completed successfully.')
    else:
      log.warn('Subprocess exited with non-zero status code {}'.format(str(exitcode)))
    return exitcode
  except Exception as e:
    log.error(traceback.print_exc())
    log.error(e)
    return 1


def try_func(f, *args, **kwargs):
  '''Run a function in a try block, logging any resulting error
  and exiting the program is directed.

  All positional and keyword arguments will be passed as arguments
  to the supplied function.

  There are two optional keyword arguments that affect this function:

  quit_on_fail: Set to true to sys.exit(1) if an exception is raised.
  log_error: Set to true report exception tracebacks to logging.error.
  '''
  try:
    result = f(*args, **kwargs)
    return result
  except:
    if log_error:
      log.error(traceback.print_exc())
      if kwargs['fail_log']:
        log.error(kwargs['fail_log'])
    if kwargs['quit_on_fail']:
      log.info("Exiting due to unrecoverable error...")
      sys.exit(1)


def init_log(level=log.DEBUG):
  '''Initialize logging.''' 
  log.basicConfig(level=level, filename='./log')
  ch = log.StreamHandler()
  logger = log.getLogger()
  logger.addHandler(ch)


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



################################# DATE HELPERS #################################


def get_year_jd_config_for_datetime(date):
  '''Given a datetime object, return a dictionary of the form
  { 'year': 'YYYY', 'jd': 'JJJ' } where JJJ is a zero-padded day of the year.
  '''
  return { 'year': date.strftime('%Y'), 'jd': date.strftime('%j') }


def validate_modis_yr_jd(year, jd):
  '''Throw an exception if a given year or julian day is invalid.'''
  if int(year) < MODIS_DATA_YEAR_START or int(year) > int(today_year):
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


def get_all_modis_data_years():
  '''Return a list of years (strings) for which MODIS data is available on the GIMMS server.'''
  start = int(MODIS_DATA_YEAR_START)
  today = datetime.datetime.today()
  this_year = today.strftime('%Y')
  all_years = list(range(start, int(this_year)+1 ))
  return [ str(y) for y in all_years ]



############################## FILE HELPERS ########################################


def harvest_products(date, dryrun):
  year = date['year']
  jd = date['jd']
  for key in PRODUCT_DIRS:
    fw2_check = 'ForWarnLAEA' if key != 'ALC' else 'ALCLAEA'
    fw2_sqrt_check = 'ForWarn2LAEA' if key != 'ALC' else 'ALC2LAEA'
    path = os.path.join('.', key)
    files = os.listdir(path)
    files = list(filter(lambda f: jd in f, files))
    for f in files:
      if fw2_check in f and year in f:
        source_dir = 'ForWarn2'
      elif fw2_sqrt_check in f and year in f:
        source_dir = 'ForWarn2_Sqrt'
      else:
        continue
      old_fullpath = os.path.join(path, f)
      new_fullpath = os.path.join('.', source_dir, PRODUCT_DIRS[key], get_new_fw2_filename_for(f))
      if os.path.isdir(os.path.join('.', source_dir, PRODUCT_DIRS[key])):
        logging.info("Moving {0}\n to \n{1}\n".format(old_fullpath, new_fullpath, date))
        shutil.copyfile(old_fullpath, new_fullpath)
      try_func(os.remove, old_fullpath, quit_on_fail=True)


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


def symlink_precursors(dates):
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
  jds = set(jds)
  for jd in list(jds):
    build_symlinks_by_pattern(PRECURSORS_DIR, '.', ".*\d{4}\."+jd+".*\.img") 


def destroy_symlinks_by_ext(ext='.img'):
  '''Delete any symlinks in the current directory that have a certain file extension (default is '.img')'''
  for f in os.listdir('.'):
    if os.path.islink(f) and f.endswith(ext) and not os.path.isdir(f):
      os.remove(f) 


def build_symlinks_by_pattern(source_dir, dest_dir, pattern, dryrun=False):
  '''Recursively walk source_dir and make a symlink in dest_dir for every file found if the file matches the supplied pattern.'''
  log.info("Making symlinks for all files found in {} into {} that match this pattern: {}".format(source_dir, dest_dir, pattern))
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
                log.info("Linking {}...".format(src))
              except:
                pass
          else:
              pass

  if not found_at_least_one_match:
    log.warn("No files found to make symbolic links for!")


def archive_new_precursors(base_dir='.', ext='.img'):
  '''Move any precursor files (hard links only) in the current directory to the archive.'''
  all_jds = ALL_MODIS_JULIAN_DAYS
  files = os.listdir(base_dir)
  for f in files:
    if f.endswith(ext) and not os.path.islink(f):
      for jd in all_jds:
        if re.search(".*\d{4}\."+jd+".*"+ext+"$", f):
          new_path = os.path.join(PRECURSORS_DIR, jd, f)
          log.info("Moving {} to {}...".format(f, new_path))
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


