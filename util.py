import smtplib
from email.message import EmailMessage

from subprocess import Popen, PIPE, STDOUT
import os, os.path, sys, re, traceback, shutil, datetime
from pytz import timezone

from tempfile import NamedTemporaryFile
import base64
import logging as log

# Some helpful constants

ALL_MODIS_JULIAN_DAYS=("001", "009", "017", "025", "033", "041", "049", "057", "065", "073", "081", "089", "097", "105", "113", "121", "129", "137", "145", "153", "161", "169", "177", "185", "193", "201", "209", "217", "225", "233", "241", "249", "257", "265", "273", "281", "289", "297", "305", "313", "321", "329", "337", "345", "353", "361")

# ForWarn 2 julian days are the same as MODIS, except we exclude day 361
# However, we still build precursors for day 361 since it's used when calculating
# products for days 001 and 009.
ALL_FW2_JULIAN_DAYS=ALL_MODIS_JULIAN_DAYS[:-1]

# Each tuple is a triplet of MODIS product days corresponding to
# a ForWarn 2 product window for the first day in the tuple.
INTERVALS=[ ("361","353","345"), ("353","345","337"), ("345","337","329"), ("337","329","321"), ("329","321","313"), ("321","313","305"), ("313","305","297"), ("305","297","289"), ("297","289","281"), ("289","281","273"), ("281","273","265"), ("273","265","257"), ("265","257","249"), ("257","249","241"), ("249","241","233"), ("241","233","225"), ("233","225","217"), ("225","217","209"), ("217","209","201"), ("209","201","193"), ("201","193","185"), ("193","185","177"), ("185","177","169"), ("177","169","161"), ("169","161","153"), ("161","153","145"), ("153","145","137"), ("145","137","129"), ("137","129","121"), ("129","121","113"), ("121","113","105"), ("113","105","097"), ("105","097","089"), ("097","089","081"), ("089","081","073"), ("081","073","065"), ("073","065","057"), ("065","057","049"), ("057","049","041"), ("049","041","033"), ("041","033","025"), ("033","025","017"), ("025","017","009"), ("017","009","001"), ("009","001","361"), ("001","361","353") ]


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


## Exceptions
#

class DataNotFoundError(Exception):
  pass

class InvalidDateError(Exception):
  pass

class OverwriteError(Exception):
  pass


## Helpers
#

def run_process(cmd, remove_newlines=True):
  log.info('Running subprocess...')
  log.info(f'{cmd}')
  if remove_newlines:
    cmd = cmd.replace('\n', '')
  cmd = cmd.strip()
  process = Popen(cmd, stdout=PIPE, stderr=STDOUT, shell=True)
  with process.stdout:
    for line in iter(process.stdout.readline, b''):
      log.info(line.rstrip().decode("utf-8"))
  exitcode = process.wait()
  if exitcode > 0:
    raise OSError(f"Process returned with non-zero exit code: {exitcode}.")


def get_default_log_path():
  now = get_now_est(time_format=LOG_FILE_TIMESTAMP_FORMAT)
  log_path = LOG_PATH_TEMPLATE.format(now)
  return log_path


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
  file_handler = log.FileHandler(filename=log_path or get_default_log_path(), mode='a')
  stream_handler = log.StreamHandler()
  logger.addHandler(file_handler)
  logger.addHandler(stream_handler)
  for handler in logger.handlers[:]:
    handler.setFormatter(formatter)
  logger.setLevel(level)


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
    body_text += "Summary:\n\n"
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
  me = 'nemacmailer@gmail.com'
  msg['Subject'] = subject_text
  msg['From'] = me
  msg['To'] = ', '.join(mail_to_addrs)
  msg.set_content(body_text)
  msg.add_attachment(log_contents, filename=os.path.basename(log_path))
  s = smtplib.SMTP('localhost', 25)
  s.send_message(msg)
  s.quit()


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
    log.info("Another instance of {} is already running! Or it's open in a text editor (LOL). Exiting...".format(name_of_this_script))
    sys.exit() 


def delete_staging_precursors(base_dir='.', ext='img', dryrun=False):
  '''Remove staging precursor files with file extension {ext} in {base_dir}.

  This function removes any file ending in {img} in the folder {base_dir} that
  is NOT a maxMODIS or maxMODISmax precursor.'''
  staging_precursors = [
    '10thallpriormax',
    '90thallpriormax',
    'maxMODISalc',
    'maxMODISmax90.10-yr-baseline',
    'maxMODISmax90.5-yr-baseline',
    'maxMODIS.1-yr-baseline',
    'maxMODISmaxmax.1-yr-baseline',
    'maxMODISmaxmax.3-yr-baseline',
    'maxMODISmaxmax.5-yr-baseline',
    'medianallpriormax'
  ]
  all_jds = ALL_MODIS_JULIAN_DAYS
  files = os.listdir(base_dir)
  for f in files:
    if f.endswith(ext) and not os.path.islink(f):
      # only move maxMODIS and maxMODISmax precursors
      for s in staging_precursors:
        if s in f:
          log.info("Removing staging precursor {}".format(f))
          if not dryrun:
            p = os.path.realpath(os.path.join(base_dir, f))
            os.remove(p)
  if 'Aqua.img' in files and not dryrun:
    os.remove(os.path.join(base_dir, 'Aqua.img'))
  if 'Terra.img' in files and not dryrun:
    os.remove(os.path.join(base_dir, 'Terra.img'))

