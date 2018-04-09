import datetime, json, logging, math, os, pprint
import requests

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
        self.NUMBER_OF_CHUNKS = int( os.environ['SBE__NUMBER_OF_CHUNKS'] )

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
            Called by controller.check_tracker_file() """
        if not tracker['last_bib']:
            r = requests.get( self.LASTBIB_URL )
            tracker['last_bib'] = r.json()['entries'][0]['id']
            tracker['last_updated'] = str( datetime.datetime.now() )
            with open(self.TRACKER_FILEPATH, 'wb') as f:
                f.write( json.dumps(tracker, sort_keys=True, indent=2).encode('utf-8') )
        log.debug( 'tracker, ```%s```' % pprint.pformat(tracker) )
        return tracker

    def check_tracker_batches( self, tracker, start_bib, end_bib ):
        """ Checks for batches and creates them if they don't exist.
            Called by check_tracker_file() """
        if tracker['batches']:
            return
        tracker = self.prepare_tracker_batches( tracker, start_bib, end_bib )
        with open(self.TRACKER_FILEPATH, 'wb') as f:
            f.write( json.dumps(tracker, sort_keys=True, indent=2).encode('utf-8') )
        log.debug( 'tracker, ```%s```' % pprint.pformat(tracker) )
        return tracker

    def prepare_tracker_batches( self, tracker, start_bib, end_bib ):
        """ Prepares the batches.
            Called by check_tracker_batches() """
        full_bib_range = end_bib - start_bib
        chunk_number_of_bibs = math.ceil( full_bib_range / self.NUMBER_OF_CHUNKS )  # by rounding up the last batch will be sure to include the `end_bib`
        ( chunk_start_bib, chunk_end_bib ) = ( start_bib, start_bib + chunk_number_of_bibs )
        for i in range( 0, self.NUMBER_OF_CHUNKS ):
            chunk_dct = { 'chunk_start_bib': chunk_start_bib, 'chunk_end_bib': chunk_end_bib, 'last_grabbed': None }
            tracker['batches'].append( chunk_dct )
            ( chunk_start_bib, chunk_end_bib ) = ( chunk_start_bib + chunk_number_of_bibs, chunk_end_bib + chunk_number_of_bibs )
        tracker['last_updated'] = str( datetime.datetime.now() )
        log.debug( 'tracker, ```%s```' % pprint.pformat(tracker) )
        return tracker

    def get_next_batch( self, tracker ):
        """ Returns the next batch of bibs to grab.
            Called by controller.manage_download() """
        batch = None
        for entry in tracker['batches']:
            twentyfour_hours_ago = datetime.datetime.now() + datetime.timedelta( hours=-24 )
            if entry['last_grabbed'] is None or entry['last_grabbed'] < twentyfour_hours_ago:
                batch = entry
                break
        log.debug( 'batch, ```%s```' % pprint.pformat(batch) )
        return batch

    ## end class class TrackerHelper()
