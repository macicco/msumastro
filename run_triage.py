"""
DESCRIPTION
-----------
    For each directory provided on the command line create a table
    in that directory with one row for each FITS file in the directory.
    The columns are FITS keywords extracted from the header of each
    file.

    The list of default keywords extracted is available through the command
    line option ``--list-default``.

    .. Note::
        This feature is available only from the command line.

    For more control over the parameters see :func:`triage_fits_files`

    .. Note::
        This script is **NOT RECURSIVE**; it will not process files in
        subdirectories of the the directories supplied on the command line.


EXAMPLES
--------

    Invoking this script from the command line::

        python run_triage.py /my/folder/of/images

    Get list of default keywords included in summary table::

        python run_triage.py --list-default

    To work on the same folder from within python, do this::

        from run_triage import triage_directories
        astrometry_for_directory('/my/folder/of/images')


"""
import os
import numpy as np


class DefaultFileNames(object):
    def __init__(self):
        self.object_file_name = 'NEEDS_OBJECT_NAME.txt'
        self.pointing_file_name = 'NEEDS_POINTING_INFO.txt'
        self.filter_file_name = 'NEEDS_FILTER.txt'
        self.output_table = 'Manifest.txt'


def write_list(dir, file, info, column_name='File'):
    from astropy.table import Table
    temp_table = Table(data=[info],
                       names=[column_name])
    temp_table.write(os.path.join(dir, file),
                     format='ascii')


def contains_maximdl_imagetype(image_collection):
    """
    Check an image file collection for MaxImDL-style image types
    """
    import re
    file_info = image_collection.summary_info
    image_types = ' '.join([typ for typ in file_info['imagetyp']])
    if re.search('[fF]rame', image_types) is not None:
        return True
    else:
        return False


def triage_fits_files(dir='.', file_info_to_keep=['imagetyp',
                                                  'object',
                                                  'filter']):
    """
    Check FITS files in a directory for deficient headers

    `dir` is the name of the directory to search for files.

    `file_info_to_keep` is a list of the FITS keywords to get values
    for for each FITS file in `dir`.
    """
    from feder import Feder
    from image_collection import ImageFileCollection

    all_file_info = file_info_to_keep
    feder = Feder()
    RA = feder.RA
    if 'ra' not in [key.lower() for key in all_file_info]:
        all_file_info.extend(RA.names)

    images = ImageFileCollection(dir, keywords=all_file_info)
    file_info = images.fits_summary(keywords=all_file_info)

    # check for bad image type and halt until that is fixed.
    if contains_maximdl_imagetype(images):
        raise ValueError(
            'Correct MaxImDL-style image types before proceeding.')

    file_needs_filter = \
        list(images.files_filtered(imagetyp='light',
                                   filter=''))
    file_needs_filter += \
        list(images.files_filtered(imagetyp='flat',
                                   filter=''))

    file_needs_object_name = \
        list(images.files_filtered(imagetyp='light',
                                   object=''))

    lights = file_info[file_info['imagetyp'] == 'LIGHT']
    has_no_ra = np.array([True] * len(lights))
    for ra_name in RA.names:
        try:
            has_no_ra &= (lights[ra_name] == '')
        except KeyError as e:
            pass

    needs_minimal_pointing = (lights['object'] == '') & has_no_ra

    dir_info = {'files': file_info,
                'needs_filter': file_needs_filter,
                'needs_pointing': list(lights['file'][needs_minimal_pointing]),
                'needs_object_name': file_needs_object_name}
    return dir_info


def triage_directories(directories,
                       keywords=None,
                       object_file_name=None,
                       pointing_file_name=None,
                       filter_file_name=None,
                       output_table=None):

    use_keys = []
    if keywords is not None:
        use_keys = keywords

    for currentDir in directories:
        result = triage_fits_files(currentDir, file_info_to_keep=use_keys)
        for fil in [pointing_file_name, filter_file_name,
                    object_file_name, output_table]:
            try:
                os.remove(os.path.join(currentDir, fil))
            except OSError:
                pass

        need_pointing = result['needs_pointing']
        if need_pointing:
            write_list(currentDir, pointing_file_name, need_pointing)
        if result['needs_filter']:
            write_list(currentDir, filter_file_name, result['needs_filter'])
        if result['needs_object_name']:
            write_list(currentDir, object_file_name,
                       result['needs_object_name'])
        tbl = result['files']
        if ((len(tbl) > 0) and (output_table is not None)):
            tbl.write(os.path.join(currentDir, output_table),
                      format='ascii', delimiter=',')


def construct_parser():
    from argparse import ArgumentParser
    import script_helpers

    parser = ArgumentParser()
    script_helpers.setup_parser_help(parser, __doc__)
    # allow for no directories below so that -l option
    # can be used without needing to specify a directory
    script_helpers.add_directories(parser, '*')
    script_helpers.add_verbose(parser)

    key_help = 'FITS keyword to add to table in addition to the defaults; '
    key_help += 'for multiple keywords use this option multiple times.'
    parser.add_argument('-k', '--key', action='append',
                        help=key_help)

    no_default_help = 'Do not include default list of keywords in table'
    parser.add_argument('-n', '--no-default', action='store_true',
                        help=no_default_help)

    list_help = 'Print default list keywords put into table and exit'
    parser.add_argument('-l', '--list-default', action='store_true',
                        help=list_help)

    default_names = DefaultFileNames()
    output_file_help = 'Name of file in which table is saved; default is '
    output_file_help += default_names.output_table
    parser.add_argument('-t', '--table-name',
                        default=default_names.output_table,
                        help=output_file_help)

    needs_object_help = 'Name of file to which list of files that need '
    needs_object_help += 'object name is saved; default is '
    needs_object_help += default_names.object_file_name
    parser.add_argument('-o', '--object-needed-list',
                        default=default_names.object_file_name,
                        help=needs_object_help)

    needs_pointing_help = 'Name of file to which list of files that need '
    needs_pointing_help += 'pointing name is saved; default is '
    needs_pointing_help += default_names.pointing_file_name
    parser.add_argument('-p', '--pointing-needed-list',
                        default=default_names.pointing_file_name,
                        help=needs_pointing_help)

    needs_filter_help = 'Name of file to which list of files that need '
    needs_filter_help += 'filter is saved; default is '
    needs_filter_help += default_names.filter_file_name
    parser.add_argument('-f', '--filter-needed-list',
                        default=default_names.filter_file_name,
                        help=needs_filter_help)

    return parser

if __name__ == "__main__":
    from sys import exit
    parser = construct_parser()
    args = parser.parse_args()

    all_keywords = ['imagetyp', 'filter', 'exptime', 'ccd-temp']

    always_include_keys = ['imagetyp', 'filter', 'exptime', 'ccd-temp',
                           'object', 'observer', 'airmass', 'instrument',
                           'RA', 'Dec']

    try:
        always_include_keys.extend(args.key)
    except TypeError as e:
        pass

    if args.no_default:
        always_include_keys = None

    if args.list_default:
        print 'Keys included by default are:\n'
        keys_print = [key.upper() for key in always_include_keys]
        print ', '.join(keys_print)
        exit(0)

    if not args.dir:
        parser.error('No directory specified')

    triage_directories(args.dir, keywords=always_include_keys,
                       object_file_name=args.object_needed_list,
                       pointing_file_name=args.pointing_needed_list,
                       filter_file_name=args.filter_needed_list,
                       output_table=args.table_name)
