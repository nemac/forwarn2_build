#!/bin/bash

files=$(ls *.img)

for f in $files
do
  filename=${f%%\.img}
  ./rescale_max.sh ${filename}.img ${filename}.rescaled.img
  gdal_translate -stats -co "COMPRESS=DEFLATE" -of netCDF ${filename}.rescaled.img ${filename}.nc
  rm ${filename}.rescaled.img
done
