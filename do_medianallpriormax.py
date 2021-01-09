#!/usr/bin/env python

import os, os.path, argparse
import sys


intervals = [ ("361","353","345"), ("353","345","337"), ("345","337","329"), ("337","329","321"), ("329","321","313"), ("321","313","305"), ("313","305","297"), ("305","297","289"), ("297","289","281"), ("289","281","273"), ("281","273","265"), ("273","265","257"), ("265","257","249"), ("257","249","241"), ("249","241","233"), ("241","233","225"), ("233","225","217"), ("225","217","209"), ("217","209","201"), ("209","201","193"), ("201","193","185"), ("193","185","177"), ("185","177","169"), ("177","169","161"), ("169","161","153"), ("161","153","145"), ("153","145","137"), ("145","137","129"), ("137","129","121"), ("129","121","113"), ("121","113","105"), ("113","105","097"), ("105","097","089"), ("097","089","081"), ("089","081","073"), ("081","073","065"), ("073","065","057"), ("065","057","049"), ("057","049","041"), ("049","041","033"), ("041","033","025"), ("033","025","017"), ("025","017","009"), ("017","009","001"), ("009","001","361"), ("001","361","353") ]

def get_three_dates(year, doy):
  days = list(filter(lambda trip: trip[0] == doy, intervals))[0]
  if not len(days):
    print "Invalid day of year"
    sys.exit()
  days = list(map(lambda d: (d, year), days))
  # doy == 009 or doy == 001 is a special case where the year is not consistent
  if doy == '009':
    days[2] = ( '361', str(int(year)-1) )
  if doy == '001':
    days[1] = ( '361', str(int(year)-1) )
    days[2] = ( '353', str(int(year)-1) )
  print days
  return days


def setup_arg_parser():
  parser = argparse.ArgumentParser()
  parser.add_argument('-y', '--year', help='Year')
  parser.add_argument('-d', '--doy', help='Day of year')
  return parser


def main():
  parser = setup_arg_parser()
  args = parser.parse_args()
  year = args.year
  doy = args.doy
  dates = get_three_dates(year, doy)
  max_modis_file_template = "maxMODIS.{}.{}.std.img"
  for d in dates:
    doy = d[0]
    year = d[1]
    max_filename = max_modis_file_template.format(year, doy)
    if not os.path.exists(max_filename):
      print "Missing {}. Generating now...".format(max_filename)
      os.system("./do_max {} {}".format(year, doy))
  max_modis_max_filename = "maxMODISmax.{}.{}.std.img".format(year, doy)
  print "Generating {}...".format(max_modis_max_filename)
  os.system("./do_max_max {} {} {} {} {} {}".format(
    dates[0][0], dates[0][1],
    dates[1][0], dates[1][1],
    dates[2][0], dates[2][1]
  ))

if __name__ == '__main__':
  main()
