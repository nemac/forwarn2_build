#!/bin/bash

set -v

IN_FILE=$1
OUT_FILE=$2

NODATA=255

# Values ranging [251 - 255] are reserved for mask values:
# 
#    Value   Description
#    -----   -----------
#    251     (empty)
#    252     (empty)
#    253     Invalid (out of range NDVI or NDVI_anom)
#    254     Water
#    255     No data (unfilled, cloudy, or snow contaminated)
# 
# (See https://gimms.gsfc.nasa.gov/MODIS/README.txt)

gdal_calc.py \
  -A $IN_FILE \
  --outfile=$OUT_FILE \
  --type=Byte \
  --calc="(A>=251)*255+(A<251)*(100.0*A/250.0)" \
  --NoDataValue=$NODATA \
  --debug \
  --co="COMPRESS=LZW"
