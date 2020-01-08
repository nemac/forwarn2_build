#!/bin/bash

DATETYPE=$1 # nrt or std
YEAR=$2
DOY=$3 # must be 3 digits, like 001

#################################################################
# remove existing Terra and Aqua tile tifs
rm -f GMOD09Q1.*.08d.latlon.*.6v1.NDVI.tif
rm -f GMYD09Q1.*.08d.latlon.*.6v1.NDVI.tif

#################################################################
# download 26 tiles for conus each from Aqua and from Terra

echo "Now downloading DOY " $DOY " of TYPE " $DATETYPE " for YEAR " $YEAR " via https from NASA GLAM"

# download 26 Terra tiles for conus
wget -e robots=off -nd -nv -np https://gimms.gsfc.nasa.gov/MODIS/$DATETYPE/GMOD09Q1/tif/NDVI/$YEAR/$DOY/GMOD09Q1.A$YEAR$DOY.08d.latlon.x06y0{4,5,6}.6v1.NDVI.tif.gz
wget -e robots=off -nd -nv -np https://gimms.gsfc.nasa.gov/MODIS/$DATETYPE/GMOD09Q1/tif/NDVI/$YEAR/$DOY/GMOD09Q1.A$YEAR$DOY.08d.latlon.x0{7,8,9}y0{4,5,6,7}.6v1.NDVI.tif.gz
wget -e robots=off -nd -nv -np https://gimms.gsfc.nasa.gov/MODIS/$DATETYPE/GMOD09Q1/tif/NDVI/$YEAR/$DOY/GMOD09Q1.A$YEAR$DOY.08d.latlon.x1{0,1}y0{4,5,6,7}.6v1.NDVI.tif.gz
wget -e robots=off -nd -nv -np https://gimms.gsfc.nasa.gov/MODIS/$DATETYPE/GMOD09Q1/tif/NDVI/$YEAR/$DOY/GMOD09Q1.A$YEAR$DOY.08d.latlon.x12y0{4,5,7}.6v1.NDVI.tif.gz

# download 26 Aqua tiles for conus
wget -e robots=off -nd -nv -np https://gimms.gsfc.nasa.gov/MODIS/$DATETYPE/GMYD09Q1/tif/NDVI/$YEAR/$DOY/GMYD09Q1.A$YEAR$DOY.08d.latlon.x06y0{4,5,6}.6v1.NDVI.tif.gz
wget -e robots=off -nd -nv -np https://gimms.gsfc.nasa.gov/MODIS/$DATETYPE/GMYD09Q1/tif/NDVI/$YEAR/$DOY/GMYD09Q1.A$YEAR$DOY.08d.latlon.x0{7,8,9}y0{4,5,6,7}.6v1.NDVI.tif.gz
wget -e robots=off -nd -nv -np https://gimms.gsfc.nasa.gov/MODIS/$DATETYPE/GMYD09Q1/tif/NDVI/$YEAR/$DOY/GMYD09Q1.A$YEAR$DOY.08d.latlon.x1{0,1}y0{4,5,6,7}.6v1.NDVI.tif.gz
wget -e robots=off -nd -nv -np https://gimms.gsfc.nasa.gov/MODIS/$DATETYPE/GMYD09Q1/tif/NDVI/$YEAR/$DOY/GMYD09Q1.A$YEAR$DOY.08d.latlon.x12y0{4,5,7}.6v1.NDVI.tif.gz

#################################################################

# did we get 26 each?
let numtiles=`ls -1 *.gz | wc -l`

if [ "$numtiles" == 52 ]; then
   echo "Got 52 tifs for " $YEAR $DOY
   else
      echo "ERROR: Tiles MISSING for " $YEAR $DOY " only got " $numtiles
      rm -f GMOD09Q1.*.08d.latlon.*.6v1.NDVI.tif*
      rm -f GMYD09Q1.*.08d.latlon.*.6v1.NDVI.tif*
      exit
fi

gunzip *.gz

#################################################################
# mosaic together Terra for this DOY

rm -f Terra.tif
gdal_merge.py -v -init 255 -of GTiff -o "Terra.tif"  GMOD09Q1.A$YEAR$DOY*.tif
echo "done mosaicking Terra images together"
#rm -f Terra.tif
#gdal_translate Terra.tif -of GTiff Terra.tif
#xv Terra.tif

# mosaic together Aqua for this DOY

rm -f Aqua.tif
gdal_merge.py -v -init 255 -of GTiff -o Aqua.tif  GMYD09Q1.A$YEAR$DOY.*.tif
echo "done mosaicking Aqua images together"
#rm -f Aqua.tif
#gdal_translate Aqua.tif -of GTiff Aqua.tif
#xv Aqua.tif

#################################################################
# remove existing Terra and Aqua tile tifs
rm -f GMOD09Q1.*.08d.latlon.*.6v1.NDVI.tif*
rm -f GMYD09Q1.*.08d.latlon.*.6v1.NDVI.tif*

#################################################################
# take the maximum NDVI from the Terra and Aqua 8-day composites

# if both are 253 or if both are 255 or if either are 253 with the other 255, then 255, but this is NOT nodata
# if either are 254, then 254, water

# 252 is nodata coming out

echo "taking the maximum NDVI from the Terra and Aqua 8-day composites"

OUTFILE=maxMODIS.$YEAR.$DOY.$DATETYPE

#find maxval composite of Terra and Aqua
# and propagate two mask values
gdal_calc.py --debug -A Terra.tif -B Aqua.tif --outfile=${OUTFILE}.unscaled.tif --calc="\
maximum((A<251)*A,(B<251)*B)\
+(((A==253)&(B==253))|((A==253)&(B==255))|((A==255)&(B==253))|((A==255)&(B==255)))*255\
+((A==254)|(B==254))*254\
" --format=GTiff --NoDataValue=252 --type=Byte --overwrite

rm -f maxMODIS.$YEAR.$DOY.$DATETYPE.tif
rm -f Aqua.tif
rm -f Terra.tif

./rescale_max.sh ${OUTFILE}.unscaled.tif ${OUTFILE}.tif

aws s3 cp ${OUTFILE}.tif s3://forwarn2-max-modis-tifs/$YEAR/${OUTFILE}.tif
rm ${OUTFILE}.unscaled.tif
