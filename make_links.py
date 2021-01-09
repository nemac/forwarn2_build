#!/usr/bin/env python

'''Make symbolic links by walking a source directory rescursively and making a symbolic link to each file in the destination directory.'''

import os, os.path, re
import argparse

import sys

def make_links(source_dir, dest_dir, pattern, dryrun=False):
  found_at_least_one_match = False
  print("Making symlinks for all files in {} in {} matching this pattern: {}".format(source_dir, dest_dir, pattern))
  for root, dirs, files in os.walk(source_dir):
      for filename in files:
          m = re.search(pattern, filename)
          if m:
              found_at_least_one_match = True
              src = os.path.abspath(os.path.join(root, filename))
              dst = os.path.abspath(os.path.join(dest_dir, filename))
              try:
                if not dryrun:
                  os.symlink(src, dst)
                print("Linking {}...".format(src))
              except:
                pass
          else:
              #print("Not linking {} (no match)".format(filename))
              pass

  if not found_at_least_one_match:
    print("No matches found. Try again!")


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('src', help='Source directory')
  parser.add_argument('dst', help='Destination directory')
  parser.add_argument('--pattern', default='.*', help='regex pattern to match files in src folder')
  parser.add_argument('--dryrun', action='store_true', help='Simulate a run of the script with these arguments')
  args = parser.parse_args()
  make_links(args.src, args.dst, args.pattern, args.dryrun)


if __name__ == '__main__':
  main()
