
precursor_dir = './precursors'
graph_data_dir = './graph_data'

# location of Dockerfile
build_dir = './gdal_docker'

# mounted location of source tree in docker container
dkr_build_dir = '/build'

# image tag
tag = 'gdal:2.4.2'

# name of container
name = 'fw2_build'

# not used
dkr_user = 'nappl_fswms'
dkr_group = 'nappl'
