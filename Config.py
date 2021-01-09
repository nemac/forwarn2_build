import os.path

# Dev
#PRODUCTS_BASE_PATH = '/mnt/efs/forwarn2_products/forwarn2_build_dev'
#MAIN_PATH = '/mnt/efs/forwarn2_products/forwarn2_build_dev'

# keys are where dodate dumps them
# values are product directories in ForWarn2, ForWarn2_Sqrt
#   (this is where the products are moved to)
PRODUCT_DIRS = {
	'1-yr-max' : 'X_LC_1YEAR',
	'10-yr-90' : 'X_LC_90_10_YR',
	'3-yr-max' : 'X_LC_3YEAR',
	'5-yr-90'  : 'X_LC_5YEAR',
	'ALC'      : 'X_LC_ALC_1YR',
	'median-all-yr-max' : 'X_LC_MEDIAN_ALL_YR',
	'pctprogress' : 'X_LC_PCTPROGRESS'
}

PRECURSOR_DIR = './precursors'

SOURCE_DIRS = [ 'ForWarn2', 'ForWarn2_Sqrt' ]

MAIL_TO_ADDRS_FILE = 'mail_to_addrs.txt'

EMAIL_TEMPLATE_FILE = 'mime_email_template.txt'
