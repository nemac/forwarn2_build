

import rasterio as rio
import xml.etree.ElementTree as ET

from util import *
from state import *
from precursor_archive import PrecursorArchive


load_env()

class YearMaxesArchive:

  _file_tpl = 'maxMODIS.{}.std.{}'
  
  _root_dir = './graph_data'

  def __init__(self, precursors=None, root_dir=None, dryrun=False):
    self._root_dir = root_dir or self._root_dir
    self.precursors = precursors or PrecursorArchive()

  def update(self, dryrun=False, update_precursors=False):
    all_updated = [] if not update_precursors else self.precursors.update()
    std_updated = [ d for d in all_updated if d[-1] == 'std' ]
    years_updated = sorted(set([ d[0] for d in std_updated ]))
    years_missing = self._get_missing_years()
    todo = years_updated + years_missing
    for year in todo:
      self.build_tif(year, dryrun=dryrun)

  def build_tif(self, year, dryrun=False):
    '''Build a new 46-band tif where each band represents an 8-day NDVI maximum.'''
    vrt_filename = self._build_year_vrt(year, dryrun)
    tif_filename = 'maxMODIS.{}.std.tif'.format(year)
    new_tif_path_tmp = os.path.join(self._root_dir, '{}.tmp'.format(tif_filename))
    self._gdal_translate_vrt(vrt_filename, new_tif_path_tmp, dryrun=dryrun)
    try:
      os.remove(os.path.join(self._root_dir, tif_filename))
    except:
      pass
    os.rename(new_tif_path_tmp, os.path.join(self._root_dir, tif_filename))
    os.remove(vrt_filename)

  def _get_missing_years(self):
    '''Returns a list of years (strings) with missing all-year maxes tifs'''
    tpl = ALL_YEAR_MAXES_PRECURSOR_FILENAME_TEMPLATE
    ext = ALL_YEAR_MAXES_PRECURSOR_FILE_EXT
    all_years = get_all_modis_data_years()
    return list(filter(lambda y: not os.path.exists(os.path.join(self._root_dir, tpl.format(y, ext))), all_years))

  def _gdal_translate_vrt(self, vrt_path, tif_path, dryrun=False):
    '''Use gdal_translate to convert a VRT to a GeoTIFF. Used for creating all-year maxes files.
    '''
    print(f'Converting VRT to TIF: {vrt_path} {tif_path}')
    print(f'Here is the VRT:\n')
    with open(vrt_path) as f:
      for line in f.readlines():
        print(line)

    c = f'''gdal_translate
        -of GTiff
        -co TILED=YES  
        -co COMPRESS=DEFLATE
        -co BIGTIFF=YES
        {vrt_path}
        {tif_path}
    '''
    if not dryrun:
      run_process(c)

  def _build_year_vrt(self, year, dryrun=False):
    paths = self._get_vrt_bands(year)
    bounds = self._get_extent(paths, dryrun=dryrun)
    big_vrt_name = 'maxMODIS.{}.std.vrt'.format(year)
    print("Generating VRT {}...".format(big_vrt_name))
    if dryrun:
      return big_vrt_name
    for i in range(0, len(paths)):
      band_num = str(i+1)
      path = paths[i]
      temp_vrt = self._build_8day_vrt(path, bounds=bounds, dryrun=dryrun)
      if band_num == '1':
        main_tree = ET.parse(temp_vrt)
        main_root = main_tree.getroot()
      else:
        tree = ET.parse(temp_vrt)
        root = tree.getroot()
        bandElement = root.find('VRTRasterBand')
        bandElement.attrib['band'] = band_num
        main_root.append(bandElement)
      try: os.remove(temp_vrt)
      except: pass
    main_tree.write(big_vrt_name)
    return big_vrt_name

  def _get_vrt_bands(self, year):
    '''Get a list of paths to the 8-day max files for some year.'''
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

  def _build_8day_vrt(self, path, bounds=None, vrtnodata=255, band_num=1, dryrun=False):
    '''Wrapper for gdalbuildvrt. Build a 1-band VRT.

    Arguments:
      path: path to the source file
      bounds: a python list of the form [ xmin, ymin, xmax, ymax ].
        These values are joined into a string that is passed to the -te flag.
      vrtnodata: Value to use for the -vrtnodata flag.
      band_num: Band number in the source dataset to use.
    '''
    vrtnodata = str(vrtnodata)
    band_num = str(band_num)
    temp_vrt = os.path.basename(path) + '.vrt'
    c = f'''gdalbuildvrt
      -vrtnodata {vrtnodata}
      -b {band_num}
      -overwrite
    '''
    if bounds:
      bounds_string = ' '.join([ str(num) for num in bounds ])
      c += f'-te {bounds_string} \n'
    c += f'{temp_vrt} {path}'
    if not dryrun:
      run_process(c)
    return temp_vrt
 
  def _get_extent(self, paths, dryrun=False):
    '''Returns the maximum value for each extent parameter for a list of rasters.'''
    if dryrun:
      return []
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

