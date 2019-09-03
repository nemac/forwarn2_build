#!/bin/bash

files=$(ls *.img)

for f in $files
do
  filename=${f%%\.img}
  #gdal_translate -co COMPRESS=DEFLATE -of netCDF $f ${filename}.unscaled.nc
  ./rescale_max.sh ${filename}.img ${filename}.nc
done
