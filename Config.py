import os.path

# Dev
PRODUCTS_BASE_PATH = '/fsdata4/forwarn2_products/forwarn2_build_dev'
MAIN_PATH = '/fsdata4/forwarn2_products/forwarn2_build_dev'

# Prod
# PRODUCTS_BASE_PATH = '/fsdata4/forwarn2_products/'
# MAIN_PATH = '/fsdata4/forwarn2_products/forwarn2_build_prod'

DODATE_PATH = os.path.join(MAIN_PATH, 'dodate')

TODO_DAYS_PATH = os.path.join(MAIN_PATH, 'todo_product_days')

ALL_DAYS_PATH = os.path.join(MAIN_PATH, 'all_product_days')

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

MAIL_TO_ADDRS_FILE = 'mail_to_addrs.txt'

EMAIL_TEMPLATE_FILE = 'mime_email_template.txt'
