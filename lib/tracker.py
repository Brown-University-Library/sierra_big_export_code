import datetime, json, logging, os, pprint

logging.basicConfig(
    filename=os.environ['SBE__LOG_PATH'],
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S'
    )
log = logging.getLogger(__name__)
log.debug( 'loading tracker' )


class TrackerHelper( object ):

    def __init__( self ):
        self.TRACKER_FILEPATH = os.environ['SBE__TRACKER_JSON_PATH']
        self.LASTBIB_URL = os.environ['SBE__LASTBIB_URL']


    def grab_tracker_file( self ):
        """ Returns (creates if necessary) tracker from json file.
            Called by controller.check_tracker_file() """
        try:
            with open(self.TRACKER_FILEPATH, 'rb') as f:
                tracker = json.loads( f.read() )
        except:
            with open(self.TRACKER_FILEPATH, 'wb') as f:
                tracker = {
                    'last_updated': str(datetime.datetime.now()), 'last_bib': None, 'batches': [] }
                f.write( json.dumps(tracker, sort_keys=True, indent=2).encode('utf-8') )
        log.debug( 'tracker, ```%s```' % pprint.pformat(tracker) )
        return tracker

    def check_tracker_lastbib( self, tracker):
        """ Obtains last bib if it doesn't already exist.
            Called by check_tracker_file() """
        if not tracker['last_bib']:
            r = requests.get( self.LASTBIB_URL )
            tracker['last_bib'] = r.json()['entries'][0]['id']
            tracker['last_updated'] = str( datetime.datetime.now() )
            with open(self.TRACKER_FILEPATH, 'wb') as f:
                f.write( json.dumps(tracker, sort_keys=True, indent=2).encode('utf-8') )
        log.debug( 'tracker, ```%s```' % pprint.pformat(tracker) )
        return tracker
