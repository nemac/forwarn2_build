#!/usr/bin/env python

'''Make symbolic links by walking a source directory rescursively and making a symbolic link to each file in the destination directory.'''

import os, os.path, re
import argparse

import sys

def make_links(source_dir, dest_dir, ext):
  for root, dirs, files in os.walk(source_dir):
      for filename in files:
          m = re.search("img$", filename)
          if m:
              src = os.path.abspath(os.path.join(root, filename))
              dst = os.path.abspath(os.path.join(dest_dir, filename))
              try:
                os.symlink(src, dst)
              except:
                pass
          else:
              print "Not a .{0} file, so not linking: {1}".format(ext, os.path.join(root, filename))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('src', help='Source directory')
  parser.add_argument('dst', help='Destination directory')
  parser.add_argument('--ext', default='img', help='File extension to link')
  args = parser.parse_args()
  make_links(args.src, args.dst, args.ext)


if __name__ == '__main__':
  main()
