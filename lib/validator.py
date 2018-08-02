import datetime, glob, logging, ntpath, os, pprint, shutil, sys
sys.path.append( os.path.abspath(os.getcwd()) )
from lib.tracker import TrackerHelper
from pymarc import MARCReader

logging.basicConfig(
    filename=os.environ['SBE__LOG_PATH'],
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S'
    )
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
log = logging.getLogger(__name__)
log.debug( 'loading validator module' )

tracker_helper = TrackerHelper()

os.nice( 19 )


class FileChecker( object ):

    def __init__( self ):
        self.FILE_DOWNLOAD_DIR = os.environ['SBE__FILE_DOWNLOAD_DIR']
        self.TRACKER_JSON_PATH = os.environ['SBE__TRACKER_JSON_PATH']
        self.non_marc_indicators = [
            '"description": "happens when submitted bib-range is invalid"',
            'ErrorCode(',
            '"description":"invalid_grant"'
            ''
            ]  # no longer used, here for reference

    def validate_marc_files( self ):
        """ Checks all the downloaded marc files, and changes the suffix for invalid ones.
            Called by controller -> manage_download() """
        marc_file_list = glob.glob( '%s/*.mrc' % self.FILE_DOWNLOAD_DIR )
        # marc_file_list = sorted( glob.glob( '%s/*.*' % self.FILE_DOWNLOAD_DIR ) )
        log.debug( 'marc_file_list, ```%s```' % marc_file_list )
        start = datetime.datetime.now()
        for file_path in marc_file_list:
            size_in_bytes = os.path.getsize( file_path )
            validity = self.open_and_check_file( file_path )
            if validity == False and size_in_bytes > 1000:
                log.warning( 'bad file, ```%s``` is `%s` bytes' % (file_path, size_in_bytes) )
        tracker = tracker_helper.grab_tracker_file()
        tracker_helper.update_validation_status( tracker )
        time_taken = str( datetime.datetime.now() - start )
        log.debug( 'time_taken, `%s`' % time_taken )
        return

    def open_and_check_file( self, file_path ):
        """ Opens suspicious file.
            Called by validate_marc_files() """
        validity = False
        log.debug( 'file about to be checked, ```%s```' % file_path )
        with open( file_path, 'rb' ) as fh:
            reader = MARCReader( fh )
            try:
                for record in reader:
                    pass
                validity = True
            except Exception as e:
                log.error( 'exception, `%s`' % e )
                file_name = os.path.basename( file_path )
                new_file_name = file_name.replace( '.mrc', '.txt' )
                new_file_path = '%s/%s' % ( self.FILE_DOWNLOAD_DIR, new_file_name)
                log.debug( 'moving bad-file to new_file_path, ```%s```' % new_file_path )
                shutil.move( file_path, new_file_path )
        return validity

    # def open_and_check_file( self, file_path ):
    #     """ Opens suspicious file.
    #         Called by validate_marc_files() """
    #     with open( file_path, 'rt', encoding='utf8' ) as f:
    #         content = f.read()
    #         for bad_data_check in self.non_marc_indicators:
    #             if bad_data_check in content:
    #                 file_name = os.path.basename( file_path )
    #                 new_file_name = file_name.replace( '.mrc', '.txt' )
    #                 new_file_path = '%s/%s' % ( self.FILE_DOWNLOAD_DIR, new_file_name)
    #                 log.debug( 'moving bad-file to new_file_path, ```%s```' % new_file_path )
    #                 shutil.move( file_path, new_file_path )
    #     return

    ## end class FileChecker()


if __name__ == '__main__':
    log.debug( 'starting' )
    checker = FileChecker()
    checker.validate_marc_files()
    log.debug( 'complete' )
