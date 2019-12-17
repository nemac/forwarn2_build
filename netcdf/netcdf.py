from braceexpand import braceexpand
import wget

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
  list = get_terra_and_aqua_list(type, year, dayofyear)
  print(len(list))
  #for i in list:
    #wget.download(i, './netcdf_test_dir')

def main():
  download_and_extract('std', '2019', '001')

if __name__ == '__main__':
  main()
