import glob, logging, ntpath, os, pprint, shutil
from lib.tracker import TrackerHelper


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


class FileChecker( object ):

    def __init__( self ):
        self.FILE_DOWNLOAD_DIR = os.environ['SBE__FILE_DOWNLOAD_DIR']
        self.non_marc_indicators = [
            '"description": "happens when submitted bib-range is invalid"',
            'ErrorCode(',
            '"description":"invalid_grant"'
            ]

    def validate_marc_files( self, tracker ):
        """ Checks all the downloaded marc files, and changes the suffix for invalid ones.
            Called by controller -> manage_download() """
        if tracker['files_validated']:
            log.debug( 'files already validated; returning' )
            return
        marc_file_list = glob.glob( '%s/*.mrc' % self.FILE_DOWNLOAD_DIR )
        for file_path in marc_file_list:
            size_in_bytes = os.path.getsize( file_path )
            if size_in_bytes < 1000:
                log.debug( 'file, ```%s``` is only `%s` bytes' % (file_path, size_in_bytes) )
                self.open_and_check_file( file_path )
        tracker_helper.update_validation_status( tracker )
        return

    def open_and_check_file( self, file_path ):
        """ Opens suspicious file.
            Called by validate_marc_files() """
        with open( file_path, 'rt', encoding='utf8' ) as f:
            content = f.read()
            for bad_data_check in self.non_marc_indicators:
                if bad_data_check in content:
                    file_name = os.path.basename( file_path )
                    new_file_name = file_name.replace( '.mrc', '.txt' )
                    new_file_path = '%s/%s' % ( self.FILE_DOWNLOAD_DIR, new_file_name)
                    log.debug( 'moving bad-file to new_file_path, ```%s```' % new_file_path )
                    shutil.move( file_path, new_file_path )
        return

    ## end class FileChecker()
