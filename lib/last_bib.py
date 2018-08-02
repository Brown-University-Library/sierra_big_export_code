'''
SBE__ prefix for "Sierra API Experiementation"
Code to reliably grab the truly last bib.
'''

import datetime, json, logging, os, pprint, sys
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

## make last_week_date
last_week_date = datetime.date.today() + datetime.timedelta( days=-7 )

## create start_datetime
start_datetime = '%sT00:00:00Z' % last_week_date.isoformat()

## loop
( temp_last_bib, actual_last_bib, iteration_count ) = ( None, None, 0 )
while actual_last_bib is None:
    iteration_count += 1
    ## create payload
    payload = {
        'limit': '2000', 'suppressed': False, 'fields': 'id', 'createdDate': '[%s,]' % start_datetime  }
    if temp_last_bib:
        payload['id'] = '[%s,]' % temp_last_bib
    log.debug( 'iteration_count, `%s`; payload, ```%s```' % (iteration_count, pprint.pformat(payload)) )
    ## make request
    r = requests.get( bib_url, headers=custom_headers, params=payload )
    log.debug( 'bib r.content, ```%s```' % r.content )
    tmp_bib_jdct = r.json()
    ## check results
    count_returned = tmp_bib_jdct['total']
    if count_returned < 2000:  # we're done
        actual_last_bib = tmp_bib_jdct['entries'][-1]['id']
    else:
        temp_last_bib = tmp_bib_jdct['entries'][-1]['id']
    log.debug( 'temp_last_bib, `%s`; actual_last_bib, `%s`' % (temp_last_bib, actual_last_bib) )

log.debug( 'out of loop -- temp_last_bib, `%s`; actual_last_bib, `%s`' % (temp_last_bib, actual_last_bib) )

## actually get last-bib
payload = {
    'limit': '1', 'suppressed': False, 'id': actual_last_bib  }
log.debug( 'payload, ```%s```' % payload )
r = requests.get( bib_url, headers=custom_headers, params=payload )
bib_jdct = r.json()['entries'][0]
log.debug( 'bib_jdct, ```%s```' % pprint.pformat(bib_jdct) )

# ===================================
# get local last bib data
# ===================================

stored_lastbib = None
try:
    with open( LASTBIB_JSON_PATH ) as f:
        stored_lastbib_data = json.loads( f.read() )
        # stored_lastbib = stored_lastbib_data['entries'][0]['id']
        stored_lastbib = stored_lastbib_data['id']
    log.debug( 'stored_lastbib, `%s`' % stored_lastbib )
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
    if actual_last_bib > stored_lastbib:
        log.debug( 'overwriting stored data' )
        keep_flag = False
if not keep_flag:
    with open( LASTBIB_JSON_PATH, 'w+' ) as f:
        bib_jdct['updated_with_api_data'] = datetime.datetime.now().isoformat()
        f.write( json.dumps(bib_jdct, sort_keys=True, indent=2) )
    log.debug( 'overwrite successful' )
else:
    log.debug( 'no need to overwrite' )
