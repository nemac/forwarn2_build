import rasterio as rio
import xml.etree.ElementTree as ET
import glob, os, re, datetime
from util import *

PRECURSORS_DIR = "./rescaled_precursors"
GRAPH_DATA_DIR = "./newS3Data"
currentYear = datetime.date.today().year
NT_regex = re.compile(re.escape(str(currentYear))+'.*NT.*.img$')
NR_regex = re.compile(re.escape(str(currentYear))+'.*NR.*.img$')

ALL_MODIS_JULIAN_DAYS=("001", "009", "017", "025", "033", "041", "049", "057", "065", "073", "081", "089", "097", "105", "113", "121", "129", "137", "145", "153", "161", "169", "177", "185", "193", "201", "209", "217", "225", "233", "241", "249", "257", "265", "273", "281", "289", "297", "305", "313", "321", "329", "337", "345", "353")

# Looks into the precursors directory and grabs the correct NT and NR precursors
def getListOfPrecursors():
  list_of_precursors = []
  # Go through all julian date subdirectories and look for NT and NR precursors
  for juliandate in ALL_MODIS_JULIAN_DAYS:
    jd_dir = os.path.join(PRECURSORS_DIR, juliandate)
    current_directory_list = []
    for file in os.listdir(jd_dir):
      if NR_regex.match(file) or NT_regex.match(file):
        current_directory_list.append(file)
    for file in current_directory_list:
      if len(current_directory_list) == 1:
        # We don't know if it is NT or NR so we check both and prioritize NT first
        filePath = os.path.join(jd_dir, file)
        if NT_regex.match(file):
          print('Found only one and using NT for julian date ' + juliandate)
          list_of_precursors.append(filePath)
        elif NR_regex.match(file):
          print('Found only one and using NR for julian date ' + juliandate)
          list_of_precursors.append(filePath)
      if len(current_directory_list) == 2:
        # assume that there is both an NT and an NR in this directory and only add the NT
        if NT_regex.match(file):
          print('Found two and using NT for julian date ' + juliandate)
          filePath = os.path.join(jd_dir, file)
          list_of_precursors.append(filePath)
        else:
          continue # do nothing with the NR since we're assuming there is an NT file
      if len(current_directory_list) > 2:
        raise RuntimeError('More than 2 precursors were found in subdirectory: ' + juliandate + '. Exiting.')

  return list_of_precursors

def build_year_vrt(year):
  print('building year vrt')
  paths = get_vrt_bands(year)
  bounds = get_extent(paths)
  big_vrt_name = 'maxMODIS.{}.std.vrt'.format(year)
  print("Generating VRT {}...".format(big_vrt_name))
  for i in range(0, len(paths)):
    band_num = str(i+1)
    path = paths[i]
    temp_vrt = build_8day_vrt(path, bounds=bounds)
    if band_num == '1':
      main_tree = ET.parse(temp_vrt)
      main_root = main_tree.getroot()
    else:
      tree = ET.parse(temp_vrt)
      root = tree.getroot()
      bandElement = root.find('VRTRasterBand')
      bandElement.attrib['band'] = band_num
      main_root.append(bandElement)
    try: os.remove(temp_vrt)
    except: pass
  main_tree.write(big_vrt_name)
  return big_vrt_name

# I can probably remove this since it's captured in getListOfPrecursors function
def get_vrt_bands(year):
  listOfPrecursors = getListOfPrecursors()
  return listOfPrecursors

def get_extent(paths):
  # Returns the maximum value for reach extent parameter for a list of rasters.
  check_same_proj(paths)
  def max_by_key(iterable, key):
    return max([ getattr(obj, key) for obj in iterable ])
  bounds = []
  for p in paths:
    with rio.Env():
      with rio.open(p) as src:
        bounds.append(src.bounds)
  max_bounds = [ max_by_key(bounds, key) for key in ('left', 'bottom', 'right', 'top') ]
  return max_bounds

def check_same_proj(paths):
  proj_strings = []
  for p in paths:
    with rio.Env():
      with rio.open(p) as src:
        proj_strings.append(src.profile['crs'].to_proj4())
  proj_last = proj_strings[0]
  for proj in proj_strings:
    if proj_last != proj:
      raise TypeError('All datasets must have the exact same projection!')

def build_8day_vrt(path, bounds=None, vrtnodata=255, band_num=1):
  '''Wrapper for gdalbuildvrt. Build a 1-band VRT.

  Arguments:
    path: path to the source file
    bounds: a python list of the form [ xmin, ymin, xmax, ymax ].
      These values are joined into a string that is passed to the -te flag.
    vrtnodata: Value to use for the -vrtnodata flag.
    band_num: Band number in the source dataset to use.
  '''
  vrtnodata = str(vrtnodata)
  band_num = str(band_num)
  temp_vrt = os.path.basename(path) + '.vrt'
  c = f'''gdalbuildvrt
    -vrtnodata {vrtnodata}
    -b {band_num}
    -overwrite
  '''
  if bounds:
    bounds_string = ' '.join([ str(num) for num in bounds ])
    c += f'-te {bounds_string} \n'
  c += f'{temp_vrt} {path}'
  run_process(c)
  return temp_vrt

def gdal_translate_vrt(vrt_path, tif_path):
  '''Use gdal_translate to convert a VRT to a GeoTIFF. Used for creating all-year maxes files.
  '''
  print(f'Converting VRT to TIF: {vrt_path} {tif_path}')
  #print(f'Here is the VRT:\n')
  #with open(vrt_path) as f:
  #  for line in f.readlines():
  #    print(line)

  c = f'''gdal_translate
      -of GTiff
      -co TILED=YES
      -co COMPRESS=DEFLATE
      -co BIGTIFF=YES
      {vrt_path}
      {tif_path}
  '''
  run_process(c)

# main chunk of code
# Build a new 46-band tif where each band represents an 8-day NDVI maximum.
def build_new_tif(dryrun=True):
  vrt_filename = build_year_vrt(currentYear)
  tif_filename = 'maxMODIS.{}.std.tif'.format(currentYear)
  """Check if we need to build a new tif
  There is some inefficiency and redundancy here but it works
  Check number of files in list of precursors and if it's the same as the bands
  Then do nothing since we do not need to build a new tif"""
  try:
    number_of_precursors = len(getListOfPrecursors())
    number_of_bands_in_raster = rio.open(os.path.join(GRAPH_DATA_DIR, tif_filename)).count
    if (number_of_precursors == number_of_bands_in_raster):
      print("All precursors are currently in the tif. Number of precursors found: " + str(number_of_precursors))
      return
  except:
    print('check for bands in tif failed. Rebuilding tif')
    pass
  new_tif_path_tmp = os.path.join(GRAPH_DATA_DIR, '{}.tmp'.format(tif_filename))
  if(dryrun):
    print("was going to create ", vrt_filename, new_tif_path_tmp)
    return
  gdal_translate_vrt(vrt_filename, new_tif_path_tmp)
  try:
    os.remove(os.path.join(GRAPH_DATA_DIR, tif_filename))
  except:
    pass
  os.rename(new_tif_path_tmp, os.path.join(GRAPH_DATA_DIR, tif_filename))
  print('removing generated .tmp.aux.xml file')
  os.remove(os.path.join(GRAPH_DATA_DIR, tif_filename+'.tmp.aux.xml')) # remove the generated .tmp.aux.xml file
  os.remove(vrt_filename)

if __name__ == "__main__":
  build_new_tif(dryrun=False)
