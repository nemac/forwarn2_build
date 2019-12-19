from braceexpand import braceexpand
from datetime import datetime
import os, wget, gzip, shutil

def get_terra_and_aqua_list(type, year, dayofyear):
  finalList = []
  baseurl = 'https://gimms.gsfc.nasa.gov/MODIS/'
  terra = 'GMOD09Q1' # terra sudbirectory
  aqua = 'GMYD09Q1' # aqua subdirectory

  # create the list of files to be downloaded in both terra and aqua
  filenameList = list(braceexpand('.08d.latlon.x06y0{4..6}.6v1.NDVI.tif.gz'))
  filenameList += list(braceexpand('.08d.latlon.x0{7..9}y0{4..7}.6v1.NDVI.tif.gz'))
  filenameList += list(braceexpand('.08d.latlon.x1{0..1}y0{4..7}.6v1.NDVI.tif.gz'))
  filenameList += list(braceexpand('.08d.latlon.x12y0{4,5,7}.6v1.NDVI.tif.gz'))

  for i in filenameList:
    fullUrlPath = baseurl + type + '/' + terra + '/tif/NDVI/' + year + '/' + dayofyear + '/' + terra + '.A' + year + dayofyear + i # full path for each terra file
    finalList.append(fullUrlPath)
    fullUrlPath = baseurl + type + '/' + aqua + '/tif/NDVI/' + year + '/' + dayofyear + '/' + aqua + '.A' + year + dayofyear + i # full path for each aqua file
    finalList.append(fullUrlPath)
  return finalList

def download_and_extract(type, year, dayofyear):
  listOfGzipFiles = []
  destinationDirectory = './'
  #destinationDirectory = './netcdf_test_dir/'
  list = get_terra_and_aqua_list(type, year, dayofyear)
  print ('Begin time download 52 tif.gz: ' + str(datetime.now()))
  for i in list:
    wget.download(i, destinationDirectory)
    listOfGzipFiles.append(i.split('/')[-1]) # Grabs just the .gz file and not the whole directory
  print ('End time download 52 tif.gz: ' + str(datetime.now()))
  print ('Begin time download extract 52 tif.gz: ' + str(datetime.now()))
  for i in (listOfGzipFiles):
    tifFile = i.strip('.gz')
    with gzip.open(destinationDirectory + i, 'r') as f_in, open(destinationDirectory + tifFile, 'wb') as f_out:
      shutil.copyfileobj(f_in, f_out)
    os.remove(destinationDirectory + i)
  print ('End time download extract 52 tif.gz: ' + str(datetime.now()))

def merge_terra_and_aqua_tif(year, dayofyear):
  print ('Begin time merge terra: ' + str(datetime.now()))
  os.system('gdal_merge.py -v -init 255 -of GTiff -o "Terra.tif"  GMOD09Q1.A$year$dayofyear*.tif')
  print ('End time merge terra: ' + str(datetime.now()))
  print ('Begin time merge aqua: ' + str(datetime.now()))
  os.system('gdal_merge.py -v -init 255 -of GTiff -o Aqua.tif  GMYD09Q1.A$year$dayofyear.*.tif')
  print ('End time merge aqua: ' + str(datetime.now()))

def main():
  print ('Begin time program: ' + str(datetime.now()))
  download_and_extract('std', '2019', '001')
  merge_terra_and_aqua_tif('2019', '001')
  print ('End time program: ' + str(datetime.now()))

if __name__ == '__main__':
  main()
