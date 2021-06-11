

from util import *
from state import *

volumes = {
  os.path.realpath(precursor_dir): {
    'bind': os.path.join(dkr_build_dir, precursor_dir),
    'mode': 'rw'
  },
  os.path.realpath(graph_data_dir): {
    'bind': os.path.join(dkr_build_dir, graph_data_dir),
    'mode': 'rw'
  },
  os.path.realpath('./ForWarn2'): {
    'bind': os.path.join(dkr_build_dir, 'ForWarn2'),
    'mode': 'rw'
  },
  os.path.realpath('./ForWarn2_Sqrt'): {
    'bind': os.path.join(dkr_build_dir, 'ForWarn2_Sqrt'),
    'mode': 'rw'
  }
}

def get_cli_args():
  '''Initialize the command-line argument-parser.'''
  default_log_path = LOG_PATH_TEMPLATE.format(r''+LOG_FILE_TIMESTAMP_FORMAT)
  log.info('default_log_path: ', default_log_path)
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--cron', action='store_true', help='Run the full ForWarn 2 task cycle (a normal cron job). Implies --harvest, --email, and --log. The --datestring flag will be ignored.')
  parser.add_argument('--dryrun', action='store_true', help='Run the script with no side effects.')
  # TODO
  parser.add_argument('--harvest', action='store_true', help='TODO Move ForWarn 2 products output by dodate into the local product directories into the ForWarn 2 product archive.')
  parser.add_argument('-d', '--datestring', help='TODO Build ForWarn 2 products for a certain date. The argument is of form YYYYDOY, where YYYY is a year and DOY is a day of the year, padded with zeroes if necessary. For example, 2021001 builds the ForWarn 2 product set for day 1 of 2021.')
  parser.add_argument('--email', action='store_true', help='TODO Email the results to addresses in mail_to_addrs.txt')
  parser.add_argument('--overwrite', action='store_true', help='TODO Overwrite existing products. Use at your own risk!')
  parser.add_argument('--log', action='store_true', help='TODO Keep a log. Use --log-path to override the default log path, which places the log in ./log.')
  parser.add_argument('--log-path', help='TODO Path to override the default log file (implies --log).')
  parser.add_argument('--log-level', help='Set the Python logging level.', \
    choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], \
    metavar='(CRITICAL|ERROR|WARNING|INFO|DEBUG)' \
  )
  args = parser.parse_args()
  return args


def main():
  check_is_only_instance_or_quit()
  load_env(ns=globals())
  args = get_cli_args()
  now = get_now_est(time_format='%Y%m%d_%I:%M:%S')
  if args.log or args.cron:
    log_path = get_default_log_path()
  if args.log_path:
    log_path = args.log_path
  if args.log_level:
    level = getattr(log, args.log_level)
  else:
    level = log.DEBUG
  init_log(level=level, log_path=log_path, dryrun=args.dryrun)
  if args.cron:
    all_tasks(log_path, dryrun=args.dryrun, email=args.email, harvest=True)
  elif args.datestring:
    year = datestring[:4]
    jd = datestring[-3:]
    # TODO
    #try_func(validate_modis_yr_jd, year, jd, quit_on_fail=True)


class ForWarn2Archive:

  def __init__(self):
    # ForWarn 2 products
    log.info("Building new ForWarn 2 products...")
    fw2_todo_dates = get_todo_dates_fw2_products()
    make_symlinks_for_dates(fw2_todo_dates, dryrun=dryrun)
    total_success = True
    for d in fw2_todo_dates:
      # Add a boolean called 'success' to each dict
      build_fw2_products_for(d, harvest=harvest, dryrun=dryrun)
    if not len(fw2_todo_dates):
      log.info("Already up to date!")
      os.remove(log_path)
    else:
      log.info('Finished production cycle.')
      mail_results(dates=fw2_todo_dates, dryrun=dryrun)


  def build_fw2_products_for(date, harvest=False, log_path=None, dryrun=False):
    # TODO flesh out this docstring
    '''Build a full set of ForWarn 2 products for some date.
    '''
    year = date['year']
    jd = date['jd']
    log.info("Building ForWarn 2 products for {}/{}...\n".format(year, jd))
    c = [ DODATE_PATH, '{}{}'.format(year, jd) ]
    run_subprocess(c, dryrun=dryrun)
    success = False
    # Only move result files for cron runs
    if harvest:
      harvest_products(date, dryrun=dryrun)
      if fw2_products_exist(date, dryrun=dryrun):
        success = True
      else:
        success = False
        log.error('Something went wrong while trying to move the product files to their destination.')
    date['success'] = success
    return date


