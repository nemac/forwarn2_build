
############################# CONFIG ###########################################

PRECURSORS_DIR = './precursors'
ALL_YEAR_MAXES_DIR = './graph_data'

DODATE_PATH = './dodate'

# maxMODIS.YYYY.DOY.[STD|NRT].[img]
MAX_8DAY_PRECURSOR_FILENAME_TEMPLATE = 'maxMODIS.{}.{}.{}.{}'
MAX_8DAY_PRECURSOR_FILENAME_EXT = 'img'

# maxMODIS.YYYY.std.[tif]
ALL_YEAR_MAXES_PRECURSOR_FILENAME_TEMPLATE = 'maxMODIS.{}.std.{}'
ALL_YEAR_MAXES_PRECURSOR_FILE_EXT = 'tif'


# Keys are directories used by the dodate bash script to place output files
# Values are the corresponding directory names in the product archive.
PRODUCT_DIR_MAP = {
	'1-yr-max' : 'X_LC_1YEAR',
	'10-yr-90' : 'X_LC_90_10_YR',
	'3-yr-max' : 'X_LC_3YEAR',
	'5-yr-90'  : 'X_LC_5YEAR',
	'ALC'      : 'X_LC_ALC_1YR',
	'median-all-yr-max' : 'X_LC_MEDIAN_ALL_YR',
	'pctprogress' : 'X_LC_PCTPROGRESS'
}

SOURCE_DIRS = [ 'ForWarn2', 'ForWarn2_Sqrt' ]

MAIL_TO_ADDRS_FILE = 'mail_to.txt'

EMAIL_TEMPLATE_FILE = 'email_tpl.txt'

MODIS_DATA_YEAR_START = 2003

ALL_MODIS_JULIAN_DAYS = ("001", "009", "017", "025", "033", "041", "049", "057", "065", "073", "081", "089", "097", "105", "113", "121", "129", "137", "145", "153", "161", "169", "177", "185", "193", "201", "209", "217", "225", "233", "241", "249", "257", "265", "273", "281", "289", "297", "305", "313", "321", "329", "337", "345", "353", "361")

# ForWarn 2 products are not built for day 361
ALL_FW2_JULIAN_DAYS = ALL_MODIS_JULIAN_DAYS[:-1]

INTERVALS = [ ("361","353","345"), ("353","345","337"), ("345","337","329"), ("337","329","321"), ("329","321","313"), ("321","313","305"), ("313","305","297"), ("305","297","289"), ("297","289","281"), ("289","281","273"), ("281","273","265"), ("273","265","257"), ("265","257","249"), ("257","249","241"), ("249","241","233"), ("241","233","225"), ("233","225","217"), ("225","217","209"), ("217","209","201"), ("209","201","193"), ("201","193","185"), ("193","185","177"), ("185","177","169"), ("177","169","161"), ("169","161","153"), ("161","153","145"), ("153","145","137"), ("145","137","129"), ("137","129","121"), ("129","121","113"), ("121","113","105"), ("113","105","097"), ("105","097","089"), ("097","089","081"), ("089","081","073"), ("081","073","065"), ("073","065","057"), ("065","057","049"), ("057","049","041"), ("049","041","033"), ("041","033","025"), ("033","025","017"), ("025","017","009"), ("017","009","001"), ("009","001","361"), ("001","361","353") ]

