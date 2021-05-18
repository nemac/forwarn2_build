
import unittest
import os, os.path, shutil

from gimms import Gimms, DataNotFoundError
from precursor_archive import PrecursorArchive

precursor_dir = './precursors'
test_root = './test/precursors'

tmp_dir = './tmp'
out_dir='./tmp'

year = '2021'
jd = '121'


class TestPrecursorArchive(unittest.TestCase):
  
  def setUp(self):
    self.archive = PrecursorArchive(root_dir=test_root)

  def test__update_all(self):
    pass

  def test___update_date(self):
    pass

  def test___update_24day_max(self):
    pass

  def test___update_8day_max(self):
    pass

  def test__get_24day_max_input_paths(self):
    pass

  def test__get_dir(self):
    pass

  def test___get_best_8day_max_path(self):
    pass

  def test__get_previous_date(self):
    self.assertEqual(self.archive._get_previous_date('2021', '121'), ('2021', '113'))
    self.assertEqual(self.archive._get_previous_date('2021', '001'), ('2020', '361'))

  def test__check(self):
    self.assertTrue(self.archive._check(year, jd))
    self.assertTrue(self.archive._check(year, jd, is_maxmax=True))
    self.assertFalse(self.archive._check('1800', jd))

  def test__clean(self):
    pass

  def test__update_state(self):
    pass

  def test__walk_state(self):
    pass

  def test__init_state(self):
    pass

  def test__get_file_path(self):
    path = self.archive._get_file_path(year, jd, is_maxmax=False, nrt=False, check=False)
    self.assertTrue(os.path.exists(path))
    with self.assertRaises(FileNotFoundError):
      not_here = self.archive._get_file_path('1800', '002', check=True)

  def test__filename_template(self):
    pass


@unittest.skip('skipping api test')
class TestGimms(unittest.TestCase):

  def setUp(self):
    self.sats = [ 'Aqua', 'Terra' ]
    self.api = Gimms()

  def test__get(self):
    std_path = self.api._get(year, jd, out_dir=out_dir, tmp_dir=tmp_dir, nrt=False, check=True)
    self.assertTrue(os.path.exists(std_path))
    os.remove(std_path)

  def test__get_tiles(self):
    for path in self.api._get_tiles(year, jd, sat_name='Aqua', tmp_dir=tmp_dir, nrt=False):
      self.assertTrue('GMY' in path)
      if os.path.exists(path):
        os.remove(path)

  def test__get_tile(self):
    with self.assertRaises(DataNotFoundError):
      nothing_here = self.api._get_tile(url='http://not.a.thing.abcdserfdsfs/NOTHING.IS.REAL.tif.gz', tmp_dir=tmp_dir)
    x, y, sat, ptype = '06', '04', 'GMO', 'nrt'
    url = self.api._get_tile_url(year, jd, x, y, sat, ptype)
    path = self.api._get_tile(url=url, tmp_dir=tmp_dir)
    self.assertTrue(sat in path)
    if os.path.exists(path):
      os.remove(path)

  def test__get_tile_urls(self):
    for sat_name in self.sats:
      nrt_urls = list(self.api._get_tile_urls(year, jd, sat_name=sat_name, nrt=True))
      std_urls = list(self.api._get_tile_urls(year, jd, sat_name=sat_name, nrt=False))
      self.assertEqual(len(list(nrt_urls)), 26)
      self.assertEqual(len(list(std_urls)), 26)
      for url in nrt_urls:
        self.assertTrue('nrt' in url)
        self.assertTrue(year in url)
        self.assertTrue(jd in url)
      for url in std_urls:
        self.assertTrue('std' in url)
        self.assertTrue(year in url)
        self.assertTrue(jd in url)

  def test__filename_template(self):
    sat = self.sats[0]
    prefix = 'maxMODIS'
    ext = 'img'
    f_nrt = self.api._filename_template(year, jd, nrt=True, prefix=prefix, ext=ext)
    f_std = self.api._filename_template(year, jd, nrt=False, prefix=prefix, ext=ext)
    f_sat = self.api._filename_template(year, jd, sat_name='Aqua', nrt=False, prefix=prefix, ext=ext)
    self.assertTrue('nrt' in f_nrt)
    self.assertTrue('std' in f_std)
    self.assertTrue(sat in f_sat)
    self.assertTrue(f_nrt.startswith(prefix))
    self.assertTrue(f_std.startswith(prefix))
    self.assertTrue(f_sat.startswith(prefix))
    self.assertTrue(f_nrt.endswith(ext))
    self.assertTrue(f_std.endswith(ext))
    self.assertTrue(f_sat.endswith(ext))


def link_archive(src=precursor_dir, dst=test_root):
  def copy3(src, dst):
    src = os.path.realpath(src)
    dst = os.path.realpath(dst)
    os.symlink(src, dst)
  shutil.copytree(src, dst, copy_function=copy3)

if __name__ == '__main__':
  unittest.main()
