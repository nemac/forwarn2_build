import os.path

# TODO THIS NEEDS TO BE CHANGED BACK TO /fsdata4/forwarn2_products/production FOR PRODUCTION!
PRODUCTS_BASE_PATH = '/fsdata4/forwarn2_products/forwarn2_build'

DEV_PATH = '/fsdata4/forwarn2_products/forwarn2_build'

# TODO WE WANT TO SET THIS TO THE ACTUAL PRODUCTION PATH WHEN WE'RE READY
#PRODUCTION_PATH = '/fsdata4/forwarn2_products/production'
PRODUCTION_PATH = DEV_PATH

MAIN_PATH = DEV_PATH

DODATE_PATH = os.path.join(PRODUCTION_PATH, 'dodate')

TODO_DAYS_PATH = os.path.join(PRODUCTION_PATH, 'todo_product_days')

ALL_DAYS_PATH = os.path.join(PRODUCTION_PATH, 'all_product_days')

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

SOURCE_DIRS = [ 'ForWarn2', 'ForWarn2_Sqrt' ]

EMAIL_TEMPLATE_FILE = 'mime_email_template.txt'
