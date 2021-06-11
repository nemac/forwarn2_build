import os, sys, copy
import requests
import rasterio as rio
import xml.etree.ElementTree as ET

from util import *
from state import *

from gimms import Gimms

load_env()

class PrecursorArchive:

  def __init__(self, root_dir='./precursors', year_maxes_root='./graph_data', default_file_ext='img', api=None):
    self.api = api or Gimms()
    self._jds = ALL_MODIS_JULIAN_DAYS
    self._intervals = INTERVALS
    self._default_file_ext = default_file_ext
    self._default_max_prefix = 'maxMODIS'
    self._default_maxmax_prefix = 'maxMODISmax'
    self._root_dir = os.path.realpath(root_dir)
    self._year_maxes_root = os.path.realpath(year_maxes_root)
    self._init_state()
    self._update_state()

  def update(self):
    all_updated = list(self._update_all())
    std_updated = [ d for d in all_updated if d[-1] == 'std' ]
    years_updated = sorted(set([ d[0] for d in std_updated ]))
    return years_updated

  def _get_8day_max_paths_for_yr(self, year):
    paths = []
    for jd in self._jds:
      try:
        path, nrt = self._get_best_8day_max_path(year, jd)
        if not nrt:
          paths.append({ 'jd': jd, 'path': path })
      except:
        pass
    last_jd = paths[-1]['jd']
    last_jd_i = self._jds.index(last_jd)
    assert self._jds[last_jd_i] == last_jd
    paths = [ d['path'] for d in paths ]
    not_found = False
    for jd in self._jds:
      try:
        p = self._get_file_path(year, jd, check=True)
        if not_found:
          raise DataNotFoundError('Missing std file for {year}!')
      except FileNotFoundError as e:
        not_found = True
        continue
    return paths

  def _check_same_proj(self, paths):
    proj_strings = []
    for p in paths:
      with rio.Env():
        with rio.open(p) as src:
          proj_strings.append(src.profile['crs'].to_proj4())
    proj_last = proj_strings[0]
    for proj in proj_strings:
      if proj_last != proj:
        raise TypeError('All datasets must have the exact same projection!')

  def _get_largest_extent(self, paths):
    self._check_same_proj(paths)
    def max_by_key(iterable, key):
      return max([ getattr(obj, key) for obj in iterable ])
    bounds = []
    for p in paths:
      with rio.Env():
        with rio.open(p) as src:
          bounds.append(src.bounds)
    max_bounds = [ max_by_key(bounds, key) for key in ('left', 'bottom', 'right', 'top') ]
    return max_bounds

  def _build_year_vrt(self, year, tmp_dir='./tmp'):
    paths = self._get_8day_max_paths_for_yr(year)
    bounds = self._get_largest_extent(paths)
    img_filename = self._filename_template(year, None, year_only=True)
    tmp_vrt_filename = f'{img_filename}.vrt'
    year_vrt_path = os.path.join(tmp_dir, tmp_vrt_filename)
    for i in range(0, len(paths)):
      band_num = str(i+1)
      path = paths[i]
      temp_vrt = self._build_8day_max_vrt(path, bounds=bounds)
      if band_num == '1':
        main_tree = ET.parse(temp_vrt)
        main_root = main_tree.getroot()
      else:
        tree = ET.parse(temp_vrt)
        root = tree.getroot()
        bandElement = root.find('VRTRasterBand')
        bandElement.attrib['band'] = band_num
        source_element = bandElement.find('ComplexSource')
        filename_element = source_element.find('SourceFilename')
        filename_element.text = path
        filename_element.attrib['relativeToVRT'] = "0"
        main_root.append(bandElement)
      try: os.remove(temp_vrt)
      except: pass
    main_tree.write(year_vrt_path)
    return year_vrt_path

  def _build_8day_max_vrt(self, path, tmp_dir='./tmp', bounds=None, vrtnodata=255, band_num=1):
    print(path)
    cmd = f'''
      gdalbuildvrt
        -vrtnodata "{str(vrtnodata)}"
        -b {str(band_num)}'''
    tmp_vrt_path = f'{path}.vrt'
    if bounds:
      bounds_string = ' '.join([ str(num) for num in bounds ])
      cmd += f'''
        -te { bounds_string }'''
    cmd += f'''
        {tmp_vrt_path}
        {path}
    '''
    run_process(cmd)
    return tmp_vrt_path

  def _get_width_height(self, path):
    with rio.open(path) as f:
      width = f.profile['width']
      height = f.profile['height']
    return width, height

  def _get_crs(self, path):
    with rio.open(path) as f:
      crs = f.crs
    return crs

  def _get_profile(self, path):
    with rio.open(path) as f:
      profile = f.profile
    return profile

  def _update_all(self):
    self._update_state()
    for d, y, jd in self._walk_state():
      out_path, ptype, updated = self._update_date(y, jd)
      if updated:
        yield y, jd, out_path, ptype
      self._clean()
    self._update_state()

  def _update_date(self, y, jd):
    out_path, ptype, updated = self._update_24day_max(y, jd)
    return out_path, ptype, updated

  def _update_24day_max(self, y, jd):
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
      return std_path, 'std', False
    print(f'Updating 24-day max for {y} / {jd}...')
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
    cmd = f'''
      gdal_calc.py
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
        --debug
    '''
    try:
      run_process(cmd)
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

  def _get_file_path(self, y, jd=None, is_maxmax=False, nrt=False, check=False, year_only=False, ext=None):
    filename = self._filename_template(y, jd, year_only=year_only, ext=ext, nrt=nrt, is_maxmax=is_maxmax)
    if not year_only:
      full_path = os.path.join(self._root_dir, jd, filename)
    else:
      full_path = os.path.join(self._year_maxes_root, filename)
    if check and not os.path.exists(full_path):
      raise FileNotFoundError(f'{full_path} does not exist on the file system.')
    real_path = os.path.realpath(full_path)
    return real_path

  def _filename_template(self, y, jd, is_maxmax=False, nrt=False, year_only=False, ext=None):
    ext = ext or self._default_file_ext
    max_prefix = self._default_max_prefix
    maxmax_prefix=self._default_maxmax_prefix
    prefix = maxmax_prefix if is_maxmax else max_prefix
    ptype = 'nrt' if nrt else 'std'
    if not year_only:
      filename = f'{prefix}.{y}.{jd}.{ptype}.{ext}'
    else:
      filename = f'{prefix}.{y}.{ptype}.{ext}'
    return filename
