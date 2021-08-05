
from util import load_env

load_env(ns=globals())

def get_test_dir(folder):
    return os.path.join('./test', folder)

def link_archive(src=PRECURSORS_DIR, dst=get_test_dir(PRECURSORS_DIR)):
  def copy3(src, dst):
    src = os.path.realpath(src)
    dst = os.path.realpath(dst)
    os.symlink(src, dst)
  shutil.copytree(src, dst, copy_function=copy3)

