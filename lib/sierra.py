import json, logging, os, time
import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(
    filename=os.environ['SBE__LOG_PATH'],
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S'
    )
log = logging.getLogger(__name__)
log.debug( 'loading sierra module' )


class MarcHelper( object ):

    def __init__( self ):
        self.API_ROOT_URL = os.environ['SBE__ROOT_URL']
        self.HTTPBASIC_KEY = os.environ['SBE__HTTPBASIC_USERNAME']
        self.HTTPBASIC_SECRET = os.environ['SBE__HTTPBASIC_PASSWORD']
        self.FILE_DOWNLOAD_DIR = os.environ['SBE__FILE_DOWNLOAD_DIR']
        self.chunk_number_of_bibs = json.loads( os.environ['SBE__CHUNK_NUMBER_OF_BIBS_JSON'] )  # normally null -> None, or an int

    def get_token( self ):
        """ Gets API token.
            Called by controller.download_file() """
        token_url = '%stoken' % self.API_ROOT_URL
        log.debug( 'token_url, ```%s```' % token_url )
        r = requests.post( token_url, auth=HTTPBasicAuth(self.HTTPBASIC_KEY, self.HTTPBASIC_SECRET) )
        log.debug( 'token r.content, ```%s```' % r.content )
        token = r.json()['access_token']
        log.debug( 'token, ```%s```' % token )
        return token

    def initiate_bibrange_request( self, token, next_batch ):
        """ Makes request that returns the marc file url.
            Called by controller.download_file() """
        try:
            file_url = self.make_bibrange_request( token, next_batch )
            return file_url
        except Exception as e:
            log.error( 'exception, ```%s```' % e )
            time.sleep( 10 )
            try:
                file_url = self.make_bibrange_request( token, next_batch )
                return file_url
            except Exception as e:
                log.error( '2nd exception, ```%s```; quitting' % e )
                sys.exit()

    def make_bibrange_request( self, token, next_batch ):
        start_bib = next_batch['chunk_start_bib']
        end_bib = next_batch['chunk_end_bib'] if self.chunk_number_of_bibs is None else start_bib + self.chunk_number_of_bibs
        # end_bib = next_batch['chunk_end_bib']
        marc_url = '%sbibs/marc' % self.API_ROOT_URL
        payload = { 'id': '[%s,%s]' % (start_bib, end_bib), 'limit': (end_bib - start_bib) + 1 }
        log.debug( 'payload, ```%s```' % payload )
        custom_headers = {'Authorization': 'Bearer %s' % token }
        r = requests.get( marc_url, headers=custom_headers, params=payload )
        log.debug( 'bib r.content, ```%s```' % r.content )
        file_url = r.json()['file']
        log.debug( 'file_url, ```%s```' % file_url )
        return file_url

    # def initiate_bibrange_request( self, token, next_batch ):
    #     """ Makes request that returns the marc file url.
    #         Called by controller.download_file() """
    #     start_bib = next_batch['chunk_start_bib']
    #     end_bib = next_batch['chunk_end_bib'] if self.chunk_number_of_bibs is None else start_bib + self.chunk_number_of_bibs
    #     # end_bib = next_batch['chunk_end_bib']
    #     marc_url = '%sbibs/marc' % self.API_ROOT_URL
    #     payload = { 'id': '[%s,%s]' % (start_bib, end_bib), 'limit': (end_bib - start_bib) + 1 }
    #     log.debug( 'payload, ```%s```' % payload )
    #     custom_headers = {'Authorization': 'Bearer %s' % token }
    #     r = requests.get( marc_url, headers=custom_headers, params=payload )
    #     log.debug( 'bib r.content, ```%s```' % r.content )
    #     file_url = r.json()['file']
    #     log.debug( 'file_url, ```%s```' % file_url )
    #     return file_url

    def grab_file( self, token, file_url, file_name ):
        """ Downloads file.
            Called by controller.download_file() """
        custom_headers = {'Authorization': 'Bearer %s' % token }
        r = requests.get( file_url, headers=custom_headers )
        filepath = '%s/%s' % ( self.FILE_DOWNLOAD_DIR, file_name )
        with open(filepath, 'wb') as file_handler:
            for chunk in r.iter_content( chunk_size=128 ):
                file_handler.write( chunk )
        log.debug( 'file written to ```%s```' % filepath )
        return

    ## end of MarcHelper()


