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
        # bib_range = ( 2158000, 2160000 )  # has records
        # bib_range = ( 2160000, 2162000 )  # no records (continue)
        bib_range = ( 5470000, 5472000 )  # `External Process Failed` (continue)
        try:
            token = self.get_token()
            ( file_url, err ) = self.make_bibrange_request( token, bib_range )
            if err:
                try:
                    bibrange_response_dct = json.loads( err )
                    if bibrange_response_dct.get( 'outputRecords', None ) == 0:
                        file_name = '%s_file.mrc' % str( datetime.datetime.now() ).replace( ' ', 'T' )
                        self.save_file( err, file_name)
                    elif bibrange_response_dct.get( 'name', None ) == 'External Process Failed' or bibrange_response_dct.get( 'name', None ) == 'Rate exceeded for endpoint':
                        file_name = '%s_file.mrc' % str( datetime.datetime.now() ).replace( ' ', 'T' )
                        self.save_file( err, file_name)
                except Exception as e:
                    message = 'problem reading error as json, ```%s``; raising Exception'
                    log.error( message )
                    raise Exception( message )
            if file_url:
                file_name = '%s_file.mrc' % str( datetime.datetime.now() ).replace( ' ', 'T' )
                self.grab_file( token, file_url, file_name )
        except Exception as e:
            message = 'exeption, ```%s```' % e
            log.error( message )
            raise Exception( message )
        return

    def get_token( self ):
        """ Gets API token.
            Called by manage_download() """
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

    def make_bibrange_request( self, token, bib_range ):
        """ Forms and executes the bib-range query.
            Called by manage_download() """
        start_bib = bib_range[0]
        end_bib = bib_range[1]
        marc_url = '%sbibs/marc' % self.API_ROOT_URL
        payload = { 'id': '[%s,%s]' % (start_bib, end_bib), 'limit': (end_bib - start_bib) + 1, 'mapping': 'toc' }
        log.debug( 'payload, ```%s```' % payload )
        custom_headers = { 'Authorization': 'Bearer %s' % token }
        r = requests.get( marc_url, headers=custom_headers, params=payload, timeout=30 )
        ( file_url, err ) = self.assess_bibrange_response( r )
        log.debug( 'returning file_url, ```%s```' % file_url )
        log.debug( 'returning err, ```%s```' % err )
        return ( file_url, err )

    def assess_bibrange_response( self, r ):
        """ Analyzes bib-range response.
            Called by make_bibrange_request() """
        log.debug( 'r.status_code, `%s`' % r.status_code )
        log.debug( 'bib r.content, ```%s```' % r.content )
        file_url = err = None
        #
        if r.status_code == 500:
            try:
                response_message = r.json()['name']
            except Exception as e:
                message = 'could not read response-message, ```%s```; raising Exception' % e
                log.error( message )
                raise Exception( message )
            if response_message  == 'External Process Failed': ## the failure happens reliably on certain bib-ranges. TODO: ask iii why, but continue for now
                log.warning( 'found response "%s"; returning this bib-range-response to continue' % response_message )
                err = r.content
                return ( file_url, err )
            elif response_message  == 'Rate exceeded for endpoint':  ## don't continue; stop until cron re-initiates
                message = 'found response "%s"; raising Exception' % response_message
                log.error( message )
                raise Exception( message )
            else:
                message = 'unhandled bib-range-response found, ```%s```; raising Exception' % response_message
                log.error( message )
                raise Exception( message )
        #
        if r.status_code == 200:
            try:
                data_dct = r.json()
            except Exception as e:
                message = 'response not json, ```%s```; raising Exception'
                log.error( message )
                raise Exception( message )
            try:
                if data_dct['outputRecords'] == 0:
                    log.info( 'no records found for this bib-range, returning bib-range-response to continue' )
                    err = r.content
                    return ( file_url, err )
            except Exception as e:
                message = '`outputrecords` not found in response; exception is ```%s```; raising Exception' % e
                log.error( message )
                raise Exception( message )
            try:  # happy-path
                file_url = data_dct['file']
                if file_url:
                    log.debug( 'normal file_url found, it is ```%s```' % file_url )
                    return ( file_url, err )
            except Exception as e:
                message = '`file` not found in response; exception is ```%s```; raising Exception' % e
                log.error( message )
                raise Exception( message )
        #
        if r.status_code is not 200 and r.status_code is not 500:
            message = 'unhandled status code, `%s`; raising Exception' % r.status_code
            log.error( message )
            raise Exception( message )

    def grab_file( self, token, file_url, file_name ):
        """ Downloads file.
            Called by manage_download() """
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

    def save_file( self, err_output, file_name ):
        """ Saves file.
            Called by manage_download() """
        filepath = '%s/%s' % ( self.FILE_DOWNLOAD_DIR, file_name )
        log.debug( 'filepath, ```%s```' % filepath )
        try:
            with open(filepath, 'wb') as file_handler:
                file_handler.write( err_output )
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
