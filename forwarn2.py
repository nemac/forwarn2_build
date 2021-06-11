
from util import *
from state import *

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


