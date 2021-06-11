
import subprocess
import os, gzip, glob, shutil
import requests

from util import *

class Gimms:

  _file_ext = 'img'

  _file_prefix = 'maxMODIS'

  _tilesets = [
    { 'x': ['06'], 'y': ['04', '05', '06'] },
    { 'x': ['07', '08', '09'], 'y': [ '04', '05', '06', '07' ] },
    { 'x': ['10', '11'], 'y': ['04', '05', '06', '07' ] },
    { 'x': ['12'], 'y': ['04', '05', '07'] }
  ]

  _satellites = { 'Terra': 'GMO', 'Aqua': 'GMY' }

  _url_template = 'https://gimms.gsfc.nasa.gov/MODIS/{ptype}/{sat}D09Q1/tif/NDVI/{year}/{jd}/{sat}D09Q1.A{year}{jd}.08d.latlon.x{x}y{y}.6v1.NDVI.tif.gz'
 
  def _filename_template(self, year, jd, sat_name=None, nrt=False, prefix=None, ext=None):
    ext = ext or self._file_ext
    prefix = prefix or self._file_prefix
    ptype = 'nrt' if nrt else 'std'
    if not sat_name:
      filename = f'{prefix}.{year}.{jd}.{ptype}.{ext}'
    else:
      filename = f'{prefix}.{year}.{jd}.{ptype}.{sat_name}.{ext}'
    return filename

  def check(self, year, jd, nrt=False):
    ptype = 'NRT' if nrt else 'STD'
    print('Checking GIMMS server for {ptype} / {year} / {jd}...')
    b = self._check_date(year, jd, nrt=nrt)
    return b

  def _check_date(self, year, jd, nrt=False):
    ptype = 'nrt' if nrt else 'std'
    for sat_name in self._satellites.keys():
      for url in self._get_tile_urls(year=year, jd=jd, sat_name=sat_name, nrt=nrt):
        r = requests.head(url)
        if not r.ok:
          raise DataNotFoundError(f'GIMMS {ptype} data not available for {year} / {jd}.')

  def get(self, year, jd, out_dir='.', tmp_dir='./tmp', nrt=False, check=False):
    out_path = self._get(year, jd, out_dir=out_dir, tmp_dir=tmp_dir, nrt=nrt, check=check)
    return out_path

  def _get(self, year, jd, out_dir='.', tmp_dir='./tmp', nrt=False, check=False):
    out_path = os.path.join(out_dir, self._filename_template(year, jd, nrt=nrt))
    ptype = 'nrt' if nrt else 'std'
    if os.path.exists(out_path):
      print(f'Found {out_path}...')
      return out_path
    print(f'Creating 8-day {ptype} Aqua/Terra maximum for {year} / {jd}...')
    if not os.path.exists(tmp_dir):
      os.mkdir(tmp_dir)
    if not os.path.exists(out_dir):
      os.mkdir(out_dir)
    if check:
      self._check_date(year, jd, nrt=nrt)
    # TODO output to a temporary file first instead of removing the existing one
    paths = []
    for sat_name in self._satellites.keys():
      path = os.path.join(tmp_dir, self._filename_template(year, jd, sat_name=sat_name, nrt=nrt))
      tiles = self._get_tiles(year, jd, sat_name=sat_name, tmp_dir=tmp_dir, nrt=nrt)
      error = self._merge_tiles(out_path=path, tiles=tiles)
      paths.append(path)
    p1, p2 = paths[0], paths[1]
    self._calc_max(p1=p1, p2=p2, out_path=out_path)
    return out_path

  def _get_tiles(self, year, jd, sat_name=None, tmp_dir=None, nrt=False):
    tiles = [ self._get_tile(url, tmp_dir) for url in self._get_tile_urls(year, jd, sat_name=sat_name, nrt=nrt) ]
    return tiles

  def _get_tile(self, url, tmp_dir):
    filename = url.split('/')[-1]
    gz_path = os.path.join(tmp_dir, filename)
    tif_path = gz_path.rstrip('.gz')
    if os.path.exists(tif_path):
      return tif_path
    try:
      r = requests.get(url)
    except:
      raise DataNotFoundError
    if not r.ok:
      raise DataNotFoundError
    with open(gz_path, 'wb') as fd:
      for chunk in r.iter_content(chunk_size=128):
        fd.write(chunk)
    self._gunzip(gz_path)
    return tif_path

  def _get_tile_urls(self, year, jd, sat_name=None, nrt=False):
    ptype = 'nrt' if nrt else 'std'
    sat = self._satellites[sat_name]
    for tileset in self._tilesets:
      for x in tileset['x']:
        for y in tileset['y']:
          url = self._get_tile_url(year, jd, x, y, sat, ptype)
          yield url

  def _get_tile_url(self, year, jd, x, y, sat, ptype):
    return self._url_template.format(year=year, jd=jd, x=x, y=y, sat=sat, ptype=ptype)

  def _merge_tiles(self, out_path, tiles):
    paths_str = ' '.join(tiles)
    if os.path.exists(out_path):
      print(f'Found {out_path}...')
      return out_path
    if os.path.exists(out_path):
      os.remove(out_path)
    cmd = f'''
      gdal_merge.py
        -init 255
        -of HFA
        -co "STATISTICS=YES"
        -co "COMPRESSED=YES"
        -o {out_path} {paths_str}
    '''
    run_process(cmd)
    for p in tiles:
      if os.path.exists(p):
        os.remove(p)

  def _calc_max(self, p1, p2, out_path, remove_inputs=True):
    '''Create maximum NDVI product from the Terra and Aqua 8-day composites.'''
    cmd = f'''gdal_calc.py
    -A {p1}
    -B {p2}
    --outfile={out_path}
    --calc="
      maximum((A<251)*A,(B<251)*B)
      + (
        ((A==253)&(B==253))|
        ((A==253)&(B==255))|
        ((A==255)&(B==253))|
        ((A==255)&(B==255))
      )*255
      + (
        (A==254)|(B==254)
      )*254
    "
    --format=HFA
    --co "STATISTICS=YES"
    --co "COMPRESSED=YES"
    --NoDataValue=252
    --type=Byte
    --overwrite
    '''
    run_process(cmd)
    if os.path.exists(p1) and remove_inputs:
      os.remove(p1)
    if os.path.exists(p2) and remove_inputs:
      os.remove(p2)

  def _gunzip(self, gz_path, remove=True):
    p = gz_path.rstrip('.gz')
    with gzip.open(gz_path, 'rb') as f:
      file_content = f.read()
    with open(p, 'wb') as f:
      f.write(file_content)
    if remove:
      os.remove(gz_path)

