import datetime, json, logging, os, sys, time
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
log.debug( 'loading sierra module' )


class Tester( object ):
    """ Bundles together some functions for calling directly for testing.
        Not called by other code, but via `$ python3 ./misc.py` """

    def __init__( self ):
        self.API_ROOT_URL = os.environ['SBE__ROOT_URL']
        self.HTTPBASIC_KEY = os.environ['SBE__HTTPBASIC_USERNAME']
        self.HTTPBASIC_SECRET = os.environ['SBE__HTTPBASIC_PASSWORD']
        self.FILE_DOWNLOAD_DIR = os.environ['SBE__FILE_DOWNLOAD_DIR']

    def manage_download( self ):
        """ Shot-maker.
            Called by if/main() """
        bib_range = ( 1246000, 1248000 )
        try:
            token = self.get_token()
            file_url = self.make_bibrange_request( token, bib_range )
            if file_url:
                file_name = '%s_file.mrc' % str( datetime.datetime.now() ).replace( ' ', 'T' )
                self.grab_file( token, file_url, file_name )
        except Exception as e:
            log.error( 'initial exception, ```%s```' % str(e) )
            time.sleep( 5 )
            log.debug( '\nslept 5 seconds' )
            token = self.get_token()
            file_url = self.make_bibrange_request( token, bib_range )
            if file_url:
                file_name = '%s_file.mrc' % str( datetime.datetime.now() ).replace( ' ', 'T' )
                self.grab_file( token, file_url, file_name )
        return

    def get_token( self ):
        """ Gets API token.
            Called by controller.download_file() """
        token = 'init'
        token_url = '%stoken' % self.API_ROOT_URL
        log.debug( 'token_url, ```%s```' % token_url )
        try:
            r = requests.post( token_url, auth=HTTPBasicAuth(self.HTTPBASIC_KEY, self.HTTPBASIC_SECRET), timeout=20 )
            log.debug( 'token r.content, ```%s```' % r.content )
            token = r.json()['access_token']
            log.debug( 'token, ```%s```' % token )
        except Exception as e:
            message = 'exception getting token, ```%s```' % str(e)
            log.error( message )
            raise Exception( message )
        return token

    # def initiate_bibrange_request( self, token, next_batch ):
    #     """ Makes request that returns the marc file url.
    #         Called by controller.download_file() """
    #     try:
    #         file_url = self.make_bibrange_request( token, next_batch )
    #         return file_url
    #     except Exception as e:
    #         log.error( 'exception, ```%s```' % e )
    #         time.sleep( 10 )
    #         try:
    #             file_url = self.make_bibrange_request( token, next_batch )
    #             return file_url
    #         except Exception as e:
    #             log.error( '2nd exception, ```%s```; quitting' % e )
    #             sys.exit()

    def make_bibrange_request( self, token, bib_range ):
        """ Forms and executes the bib-range query.
            Called by initiate_bibrange_request() """
        start_bib = bib_range[0]
        end_bib = bib_range[1]
        marc_url = '%sbibs/marc' % self.API_ROOT_URL
        payload = { 'id': '[%s,%s]' % (start_bib, end_bib), 'limit': (end_bib - start_bib) + 1, 'mapping': 'toc' }
        log.debug( 'payload, ```%s```' % payload )
        custom_headers = { 'Authorization': 'Bearer %s' % token }
        r = requests.get( marc_url, headers=custom_headers, params=payload, timeout=30 )
        file_url = self.assess_bibrange_response( r )
        log.debug( 'returning file_url, ```%s```' % file_url )
        return file_url

    def assess_bibrange_response( self, r ):
        """ Analyzes bib-range response.
            Called by make_bibrange_request() """
        log.debug( 'r.status_code, `%s`' % r.status_code )
        log.debug( 'bib r.content, ```%s```' % r.content )
        if r.status_code is not 200:
            message = 'bad status code; raising Exception'
            log.error( message )
            raise Exception( message )
        file_url = r.json().get( 'file', None )
        if file_url:
            log.debug( 'normal file_url found, it is ```%s```' % file_url )
            return file_url
        if r.json().get( 'name', None ) == 'Rate exceeded for endpoint':
            message = 'problem: ```Rate exceeded for endpoint; raising Exception```'
            log.error( message )
            raise Exception( message )
        elif r.json().get( 'name', None ) == 'External Process Failed':
            message = 'problem: ```External Process Failed; raising Exception```'
            log.error( message )
            raise Exception( message )
        message = 'problem, no file-url or known problem -- check r.content and handle; raising Exception'
        log.error( message )
        raise Exception( message )
        return

    def grab_file( self, token, file_url, file_name ):
        """ Downloads file.
            Called by controller.download_file() """
        log.debug( 'starting grab_file()' )
        # token = '42'
        custom_headers = {'Authorization': 'Bearer %s' % token }
        r = requests.get( file_url, headers=custom_headers )
        log.debug( 'r.status_code, `%s`' % r.status_code )
        if r.status_code is not 200:
            message = 'problem: bad status_code; r.content, ```%s```; raising Exception' % r.content
            log.error( message )
            raise Exception( message )
        filepath = '%s/%s' % ( self.FILE_DOWNLOAD_DIR, file_name )
        log.debug( 'filepath, ```%s```' % filepath )
        try:
            with open(filepath, 'wb') as file_handler:
                for chunk in r.iter_content( chunk_size=128 ):
                    file_handler.write( chunk )
                log.debug( 'file written to ```%s```' % filepath )
        except Exception as e:
            message = 'exception writing file, ```%s```; raising Exception' % e
            log.error( message )
            raise Exception( message )
        return

    ## end of Tester()


if __name__ == '__main__':
    log.debug( '\n-------\nstarting' )
    bibgetter = Tester()
    bibgetter.manage_download()
    log.debug( 'complete' )
