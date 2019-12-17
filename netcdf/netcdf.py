from braceexpand import braceexpand
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
  destinationDirectory = './netcdf_test_dir/'
  list = get_terra_and_aqua_list(type, year, dayofyear)
  wget.download('https://gimms.gsfc.nasa.gov/MODIS/std/GMOD09Q1/tif/NDVI/2019/001/GMOD09Q1.A2019001.08d.latlon.x00y09.6v1.NDVI.tif.gz', './netcdf_test_dir') # this is a test wget
  #for i in list:
  #  wget.download(i, destinationDirectory)
  for i in (os.listdir(destinationDirectory)): # find all the files we just downloaded previously
    listOfGzipFiles.append(i)
  for i in listOfGzipFiles:
    tifFile = i.strip('.gz')
    with gzip.open(destinationDirectory + i, 'r') as f_in, open(destinationDirectory + tifFile, 'wb') as f_out: #open('./netcdf_test_dir/{}'.format(i).strip('.gz'), 'wb') as f_out:
      shutil.copyfileobj(f_in, f_out)
    os.remove(destinationDirectory + i)

#def merge_terra_and_aqua_tif():
#  os.system('python3 gdal_merge')

def main():
  download_and_extract('std', '2019', '001')

if __name__ == '__main__':
  main()
