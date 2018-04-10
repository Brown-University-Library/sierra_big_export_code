'''
SBE__ prefix for "Sierra API Experiementation"
Hack to have last bib easily accessible, til I figure out how to get it via api or sql query.
'''

import datetime, json, logging, os, sys
import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(
    filename=os.environ['SBE__LOG_PATH'],
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S'
    )
log = logging.getLogger(__name__)
log.debug( '\n-------\nstarting standard log' )

if (sys.version_info < (3, 0)):
    raise Exception( 'forcing myself to use python3 always' )

API_ROOT_URL = os.environ['SBE__ROOT_URL']
HTTPBASIC_KEY = os.environ['SBE__HTTPBASIC_USERNAME']
HTTPBASIC_SECRET = os.environ['SBE__HTTPBASIC_PASSWORD']
LASTBIB_JSON_PATH = os.environ['SBE__LASTBIB_JSON_PATH']

# ===================================
# get token
# ===================================

token_url = '%stoken' % API_ROOT_URL
log.debug( 'token_url, ```%s```' % token_url )
r = requests.post( token_url, auth=HTTPBasicAuth(HTTPBASIC_KEY, HTTPBASIC_SECRET) )
log.debug( 'token r.content, ```%s```' % r.content )
token = r.json()['access_token']
log.debug( 'token, ```%s```' % token )
custom_headers = {'Authorization': 'Bearer %s' % token }  # for use in subsequent request

# ===================================
# get api last bib data
# ===================================

log.debug( '\n-------\ngetting end-bib\n-------' )
bib_url = '%sbibs/' % API_ROOT_URL
today_date = datetime.date.today().isoformat()
start_datetime = '%sT00:00:00Z' % today_date
end_datetime = '%sT23:59:59Z' % today_date
payload = {
    'limit': '1', 'createdDate': '[%s,%s]' % (start_datetime, end_datetime)  }
r = requests.get( bib_url, headers=custom_headers, params=payload )
log.debug( 'bib r.content, ```%s```' % r.content )
api_lastbib_data = r.json()
api_lastbib = r.json()['entries'][0]['id']
log.debug( 'api_lastbib, `%s`' % api_lastbib )

# ===================================
# get local last bib data
# ===================================

stored_lastbib = None
try:
    with open( LASTBIB_JSON_PATH ) as f:
        stored_lastbib_data = json.loads( f.read() )
        stored_lastbib = stored_lastbib_data['entries'][0]['id']
    log.debug( 'stored_lastbib, `%s`' % api_lastbib )
except Exception as e:
    log.error( 'exception getting stored_lastbib, ```%s```' % str(e) )
    pass

# ===================================
# compare and act
# ===================================

keep_flag = True
if stored_lastbib is None:
    log.debug( 'could not determine stored_lastbib' )
    keep_flag = False
elif stored_lastbib:
    if api_lastbib > stored_lastbib:
        log.debug( 'overwriting stored data' )
        keep_flag = False
if not keep_flag:
    with open( LASTBIB_JSON_PATH, 'w+' ) as f:
        api_lastbib_data['updated_with_api_data'] = datetime.datetime.now().isoformat()
        f.write( json.dumps(api_lastbib_data, sort_keys=True, indent=2) )
    log.debug( 'overwrite successful' )
else:
    log.debug( 'no need to overwrite' )
