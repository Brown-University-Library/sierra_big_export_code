import datetime, json, logging, math, os, pprint
import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(
    filename=os.environ['SBE__LOG_PATH'],
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S'
    )
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
log = logging.getLogger(__name__)
log.debug( 'loading tracker' )


class TrackerHelper( object ):
    """ Manages code associated with tracker.json file. """

    def __init__( self ):
        self.TRACKER_FILEPATH = os.environ['SBE__TRACKER_JSON_PATH']
        self.LASTBIB_URL = os.environ['SBE__LASTBIB_URL']
        # self.NUMBER_OF_CHUNKS = int( os.environ['SBE__NUMBER_OF_CHUNKS'] )
        self.chunk_number_of_bibs = json.loads( os.environ['SBE__CHUNK_NUMBER_OF_BIBS_JSON'] )  # normally null -> None, or an int
        self.last_bibber = LastBibHelper()

    def grab_tracker_file( self ):
        """ Returns (creates if necessary) tracker from json file.
            Called by controller.check_tracker_file() """
        try:
            with open(self.TRACKER_FILEPATH, 'rb') as f:
                tracker = json.loads( f.read() )
        except:
            with open(self.TRACKER_FILEPATH, 'wb') as f:
                tracker = {
                    'last_updated': str(datetime.datetime.now()), 'last_bib': None, 'batches': [], 'files_validated': False }
                f.write( json.dumps(tracker, sort_keys=True, indent=2).encode('utf-8') )
        log.debug( 'tracker, ```%s```' % pprint.pformat(tracker)[0:500] + '...' )
        return tracker

    def check_tracker_lastbib( self, tracker):
        """ Obtains last bib if it doesn't already exist.
            Called by controller.check_tracker_file() """
        if not tracker['last_bib']:
            try:
                r = requests.get( self.LASTBIB_URL )
                last_bib = r.json()['id']
            except Exception as e:
                log.error( 'exception, ```%s```' % str(e) )
                # last_bib = self.last_bibber.get_last_bib()
                raise Exception( 'could not obtain last_bib' )
            log.debug( 'last_bib, `%s`' % last_bib )
            tracker['last_bib'] = last_bib
            tracker['last_updated'] = datetime.datetime.now().isoformat()
            with open(self.TRACKER_FILEPATH, 'wb') as f:
                f.write( json.dumps(tracker, sort_keys=True, indent=2).encode('utf-8') )
        log.debug( 'tracker, ```%s```' % pprint.pformat(tracker)[0:500] + '...' )
        return tracker

    def check_tracker_batches( self, tracker, start_bib, end_bib ):
        """ Checks for batches and creates them if they don't exist.
            Called by check_tracker_file() """
        if tracker['batches']:
            return
        tracker = self.prepare_tracker_batches( tracker, start_bib, end_bib )
        with open(self.TRACKER_FILEPATH, 'wb') as f:
            f.write( json.dumps(tracker, sort_keys=True, indent=2).encode('utf-8') )
        log.debug( 'tracker, ```%s```' % pprint.pformat(tracker)[0:500] + '...' )
        return tracker

    def prepare_tracker_batches( self, tracker, start_bib, end_bib ):
        """ Prepares the batches.
            Called by check_tracker_batches() """
        # ( chunk_start_bib, chunk_end_bib, file_count ) = ( start_bib, start_bib + 2000, 0 )  # 2000 is api-limit
        ( chunk_start_bib, file_count ) = ( start_bib, 0 )
        chunk_end_bib = start_bib + 2000 if self.chunk_number_of_bibs is None else start_bib + self.chunk_number_of_bibs
        while chunk_start_bib < end_bib:
            chunk_dct = { 'chunk_start_bib': chunk_start_bib, 'chunk_end_bib': chunk_end_bib, 'last_grabbed': None, 'file_name': 'sierra_export_%s.mrc' % str(file_count).rjust( 4, '0' ) }
            tracker['batches'].append( chunk_dct )
            chunk_start_bib += 2000  # 2000 is api-limit
            chunk_end_bib += 2000
            file_count += 1
        tracker['last_updated'] = datetime.datetime.now().isoformat()
        log.debug( 'tracker, ```%s```' % pprint.pformat(tracker)[0:500] + '...' )
        return tracker

    def get_next_batch( self, tracker ):
        """ Returns the next batch of bibs to grab.
            Called by controller.manage_download() """
        batch = None
        for entry in tracker['batches']:
            # twentyfour_hours_ago = datetime.datetime.now() + datetime.timedelta( hours=-24 )
            # if entry['last_grabbed'] is None or datetime.datetime.strptime( entry['last_grabbed'], '%Y-%m-%dT%H:%M:%S.%f' ) < twentyfour_hours_ago:  # the second 'or' condition converts the isoformat-date back into a date-object to be able to compare
            if entry['last_grabbed'] is None:
                batch = entry
                break
        log.debug( 'batch, ```%s```' % pprint.pformat(batch) )
        return batch

    def update_tracker( self, batch, tracker ):
        """ Updates current batch information.
            Called by controller.download_file() """
        log.debug( 'tracker initially, ```%s```' % pprint.pformat(tracker)[0:500] + '...' )
        for entry in tracker['batches']:
            if entry['chunk_start_bib'] == batch['chunk_start_bib']:
                entry['last_grabbed'] = datetime.datetime.now().isoformat()
                tracker['last_updated'] = datetime.datetime.now().isoformat()
                break
        log.debug( 'tracker subsequently, ```%s```' % pprint.pformat(tracker)[0:500] + '...' )
        with open(self.TRACKER_FILEPATH, 'wb') as f:
            f.write( json.dumps(tracker, sort_keys=True, indent=2).encode('utf-8') )
        return

    def update_validation_status( self, tracker ):
        """ Sets files_validated to True.
            Called by validator.FileChecker.validate_marc_files() """
        tracker['files_validated'] = True
        tracker['last_updated'] = datetime.datetime.now().isoformat()
        with open(self.TRACKER_FILEPATH, 'wb') as f:
            f.write( json.dumps(tracker, sort_keys=True, indent=2).encode('utf-8') )
        log.debug( 'files validated; tracker updated')
        return

    ## end class class TrackerHelper()


class LastBibHelper( object):
    """ Manages code associated with getting the last-bib, required for producing the range of bibs to query. """

    def __init__( self ):
        self.API_ROOT_URL = os.environ['SBE__ROOT_URL']
        self.HTTPBASIC_KEY = os.environ['SBE__HTTPBASIC_USERNAME']
        self.HTTPBASIC_SECRET = os.environ['SBE__HTTPBASIC_PASSWORD']
        self.custom_headers = None


    def get_last_bib( self ):
        """ Controller to manage call to api to obtain last-bib.
            Called by TrackerHelper.check_tracker_lastbib()
            TODO: replace with J.M. method of posting a json query to the api to really get the last bib. """
        token = self.get_token()
        last_bib = self.get_api_last_bib( token )
        return last_bib

    def get_token( self ):
        """ Gets api token.
            Called by get_last_bib() """
        token_url = '%stoken' % self.API_ROOT_URL
        log.debug( 'token_url, ```%s```' % token_url )
        r = requests.post( token_url, auth=HTTPBasicAuth(self.HTTPBASIC_KEY, self.HTTPBASIC_SECRET) )
        log.debug( 'token r.content, ```%s```' % r.content )
        token = r.json()['access_token']
        log.debug( 'token, ```%s```' % token )
        self.custom_headers = {'Authorization': 'Bearer %s' % token }  # for use in subsequent request
        return

    def get_api_last_bib( self, token ):
        """ Hits api and obtains last bib (really first bib for last day).
            Called by get_last_bib() """
        log.debug( '\n-------\ngetting end-bib\n-------' )
        bib_url = '%sbibs/' % self.API_ROOT_URL
        today_date = datetime.date.today().isoformat()
        start_datetime = '%sT00:00:00Z' % today_date
        end_datetime = '%sT23:59:59Z' % today_date
        payload = {
            'limit': '1', 'createdDate': '[%s,%s]' % (start_datetime, end_datetime)  }
        r = requests.get( bib_url, headers=self.custom_headers, params=payload )
        log.debug( 'bib r.content, ```%s```' % r.content )
        api_lastbib = r.json()['entries'][0]['id']
        log.debug( 'api_lastbib, `%s`' % api_lastbib )
        return api_lastbib

    ## end class LastBibHelper()
