
import os, sys, copy
import requests

from util import *
from state import *

load_env()

ALL_MODIS_JULIAN_DAYS=("001", "009", "017", "025", "033", "041", "049", "057", "065", "073", "081", "089", "097", "105", "113", "121", "129", "137", "145", "153", "161", "169", "177", "185", "193", "201", "209", "217", "225", "233", "241", "249", "257", "265", "273", "281", "289", "297", "305", "313", "321", "329", "337", "345", "353", "361")

# ForWarn 2 julian days are the same as MODIS, except we exclude day 361
# However, we still build precursors for day 361 since it's used when calculating
# products for days 001 and 009.
ALL_FW2_JULIAN_DAYS=ALL_MODIS_JULIAN_DAYS[:-1]

# Each tuple is a triplet of MODIS product days corresponding to
# a ForWarn 2 product window for the first day in the tuple.
INTERVALS=[ ("361","353","345"), ("353","345","337"), ("345","337","329"), ("337","329","321"), ("329","321","313"), ("321","313","305"), ("313","305","297"), ("305","297","289"), ("297","289","281"), ("289","281","273"), ("281","273","265"), ("273","265","257"), ("265","257","249"), ("257","249","241"), ("249","241","233"), ("241","233","225"), ("233","225","217"), ("225","217","209"), ("217","209","201"), ("209","201","193"), ("201","193","185"), ("193","185","177"), ("185","177","169"), ("177","169","161"), ("169","161","153"), ("161","153","145"), ("153","145","137"), ("145","137","129"), ("137","129","121"), ("129","121","113"), ("121","113","105"), ("113","105","097"), ("105","097","089"), ("097","089","081"), ("089","081","073"), ("081","073","065"), ("073","065","057"), ("065","057","049"), ("057","049","041"), ("049","041","033"), ("041","033","025"), ("033","025","017"), ("025","017","009"), ("017","009","001"), ("009","001","361"), ("001","361","353") ]


from gimms import Gimms, DataNotFoundError


class PrecursorArchive:

  def __init__(self, root_dir='./precursors', default_file_ext='img', api=None):
    self.api = api or Gimms()
    self._jds = ALL_MODIS_JULIAN_DAYS
    self._intervals = INTERVALS
    self._default_file_ext = default_file_ext
    self._default_max_prefix = 'maxMODIS'
    self._default_maxmax_prefix = 'maxMODISmax'
    self._root_dir = root_dir
    self._init_state()
    self._update_state()

  def update(self):
    self._update_all()

  def _update_all(self):
    self._update_state()
    for d, y, jd in self._walk_state():
      self._update_date(y, jd)
      self._clean()
    self._update_state()

  def _update_date(self, y, jd):
    out_path, ptype, updated = self._update_24day_max(y, jd)
    return out_path, ptype, updated

  def _update_24day_max(self, y, jd):
    print(f'Updating 24-day max for {y} / {jd}...')
    std_path = self._get_file_path(y, jd, nrt=False, is_maxmax=True)
    nrt_path = self._get_file_path(y, jd, nrt=True, is_maxmax=True)
    y2, jd2 = self._get_previous_date(y, jd)
    y3, jd3 = self._get_previous_date(y2, jd2)
    dates = [ (y,jd), (y2,jd2), (y3,jd3) ]
    inputs_are_std = False
    try:
      paths, nrt = self._get_24day_max_input_paths(y, jd)
      if not nrt:
        inputs_are_std = True
    except FileNotFoundError:
      pass
    inputs_updated = False
    for _y, _jd, in dates:
      path, ptype, updated = self._update_8day_max(_y, _jd)
      if ptype == None:
        return None, None, False
      inputs_updated = inputs_updated or updated
    if not inputs_updated and os.path.exists(std_path):
      print(f'Found {std_path}...')
      return std_path, 'std', False
    paths, nrt = self._get_24day_max_input_paths(y, jd)
    ptype = 'nrt' if nrt else 'std'
    if inputs_updated and os.path.exists(std_path) and ptype == 'std':
      print(f'Removing outdated 24-day std max {std_path}...')
      os.remove(std_path)
    if inputs_updated and os.path.exists(nrt_path) and ptype == 'nrt':
      print(f'Removing outdated 24-day nrt max {nrt_path}...')
      os.remove(nrt_path)
    ptype = 'nrt' if nrt else 'std'
    out_path = nrt_path if nrt else std_path
    cmd = f'''gdal_calc.py --debug
      --calc="
        maximum(maximum((A<251)*A,(B<251)*B),(C<251)*C)
        +((A==254)|(B==254)|(C==254))*254
        +((A==255)&(B==255)&(C==255))*255
      "
      --NoDataValue=252
      --format=HFA
      --co "STATISTICS=YES"
      --co "COMPRESSED=YES" 
      --outfile={out_path}
      -A {paths[0]} 
      -B {paths[1]} 
      -C {paths[2]}
      --type=Byte
      --overwrite
    '''
    try:
      self.api._run_process(cmd)
    except:
      return None, None, False
    return out_path, ptype, True

  def _update_8day_max(self, y, jd):
    _dir = self._get_dir(jd)
    try:
      std_path = self._get_file_path(y, jd, nrt=False)
      if os.path.exists(std_path):
        print(f'Found std file at {std_path}...')
        return std_path, 'std', False
      std_path = self.api.get(y, jd, out_dir=_dir, check=True)
      return std_path, 'std', True
    except DataNotFoundError as e:
      print('No std data available, trying nrt instead...')
      nrt_path = self._get_file_path(y, jd, nrt=True)
      if os.path.exists(nrt_path):
        return nrt_path, 'nrt', False
      nrt_path = self.api.get(y, jd, out_dir=_dir, nrt=True, check=True)
      return nrt_path, 'nrt', True
    except DataNotFoundError as e:
      return None, None, False

  def _get_24day_max_input_paths(self, y, jd):
    y1, jd1 = y, jd
    p1, p1nrt = self._get_best_8day_max_path(y, jd)
    y2, jd2 = self._get_previous_date(y1, jd1)
    p2, p2nrt = self._get_best_8day_max_path(y2, jd2)
    y3, jd3 = self._get_previous_date(y2, jd2)
    p3, p3nrt = self._get_best_8day_max_path(y3, jd3)
    nrt = True in [ p1nrt, p2nrt, p3nrt ]
    return (p1, p2, p3), nrt
  
  def _get_dir(self, jd):
    p = os.path.join(self._root_dir, jd)
    return p
    
  def _get_best_8day_max_path(self, y, jd, std_only=False):
    std_ok = self._check(y, jd)
    if std_ok:
      nrt = False
      return self._get_file_path(y, jd), nrt
    if not std_ok and std_only:
      raise FileNotFoundError(f"No 8-day STD max found for {y} / {jd}.")
    nrt_ok = self._check(y, jd, nrt=True)
    if nrt_ok:
      return self._get_file_path(y, jd, nrt=True), nrt_ok
    raise FileNotFoundError(f"No 8-day max found for {y} / {jd}.")
 
  def _get_previous_date(self, y, jd):
    try:
      interval = [ d for d in self._intervals if d[0] == jd ][0]
    except:
      raise Exception(f"Bad year ({year}) or julian day ({jd})")
    ints = [ int(v) for v in interval ] 
    p_y = str(int(y)-1) if ints[0] < ints[1] else y
    p_jd_i = self._jds.index(jd)-1
    p_jd = self._jds[p_jd_i]
    return p_y, p_jd
    
  def _check(self, y, jd, nrt=False, is_maxmax=False):
    try:
      self._get_file_path(y, jd, nrt=nrt, is_maxmax=is_maxmax, check=True)
    except FileNotFoundError:
      return False
    return True

  def _clean(self):
    self._update_state()
    for d, y, jd in self._walk_state():
      if d['max']['std'] and d['max']['nrt']:
        path = self._get_file_path(y=y, jd=jd, nrt=True, is_maxmax=False)
        os.remove(path)
      if d['maxmax']['std'] and d['maxmax']['nrt']:
        path = self._get_file_path(y=y, jd=jd, nrt=True, is_maxmax=True)
        print(f'Removing {path}...')
        os.remove(path)
    self._update_state()

  def _update_state(self):
    for d, y, jd in self._walk_state():
      d['max']['std'] = self._check(y, jd, nrt=False, is_maxmax=False)
      d['maxmax']['std'] = self._check(y, jd, nrt=False, is_maxmax=True)
      d['max']['nrt'] = self._check(y, jd, nrt=True, is_maxmax=False)
      d['maxmax']['nrt'] = self._check(y, jd, nrt=True, is_maxmax=True)

  def _walk_state(self):
    for jd in self._state.keys():
      for y in self._state[jd].keys():
        yield self._state[jd][y], y, jd

  def _init_state(self):
    '''Example state dict:
    {
      '001': {
        '2003'': {
          'max': { 'nrt': True, 'std': False }
          'maxmax': { 'nrt': True, 'std': True }
        },
        ...
        '2021': { ... },
      },
      ...
      '353': { ... },
    }
    '''
    day_delta = 8
    state = {}
    for jd in self._jds:
      state[jd] = {}
      for y in get_all_modis_data_years():
        dt = get_datetime_for_yr_jd(y, jd)
        today = datetime.datetime.today()
        if dt > today - datetime.timedelta(days=day_delta):
          # skip unavailable dates
          continue
        s = { 'std': False, 'nrt': False }
        state[jd][y] = {}
        state[jd][y]['max'] = s
        state[jd][y]['maxmax'] = s.copy()
    self._state = state

  def _get_file_path(self, y, jd, is_maxmax=False, nrt=False, check=False):
    filename = self._filename_template(y, jd, nrt=nrt, is_maxmax=is_maxmax)
    full_path = os.path.join(self._root_dir, jd, filename)
    if check and not os.path.exists(full_path):
      raise FileNotFoundError(f'{full_path} does not exist on the file system.')
    return full_path

  def _filename_template(self, y, jd, is_maxmax=False, nrt=False):
    ext=self._default_file_ext
    max_prefix=self._default_max_prefix
    maxmax_prefix=self._default_maxmax_prefix
    prefix = maxmax_prefix if is_maxmax else max_prefix
    ptype = 'nrt' if nrt else 'std'
    filename = f'{prefix}.{y}.{jd}.{ptype}.{ext}'
    return filename
