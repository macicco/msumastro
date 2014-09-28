import os
from shutil import rmtree
from tempfile import mkdtemp
from glob import iglob, glob
import logging
import stat

import astropy.io.fits as fits
import numpy as np
import pytest
import py

from .. import image_collection as tff
from ..header_processing.patchers import IRAF_image_type
from .data import get_data_dir

_filters = []
_original_dir = ''
#triage_setup = None


def test_fits_summary(triage_setup):
    keywords = ['imagetyp', 'filter']
    image_collection = tff.ImageFileCollection(triage_setup.test_dir,
                                               keywords=keywords)
    summary = image_collection._fits_summary(header_keywords=keywords)
    print summary['file']
    print summary.keys()
    assert len(summary['file']) == triage_setup.n_test['files']
    for keyword in keywords:
        assert len(summary[keyword]) == triage_setup.n_test['files']
    # explicit conversion to array is needed to avoid astropy Table bug in
    # 0.2.4
    print np.array(summary['file'] == 'no_filter_no_object_bias.fit')
    no_filter_no_object_row = np.array(summary['file'] ==
                                       'no_filter_no_object_bias.fit')
    # there should be no filter keyword in the bias file
    assert (summary['filter'][no_filter_no_object_row].mask)


# this should work, but doesn't:
#@pytest.mark.usefixtures("triage_setup")
class TestImageFileCollection(object):
    def test_filter_files(self, triage_setup):
        img_collection = tff.ImageFileCollection(
            location=triage_setup.test_dir, keywords=['imagetyp', 'filter'])
        print img_collection.files_filtered(imagetyp='bias')
        print triage_setup.n_test
        assert len(img_collection.files_filtered(
            imagetyp='bias')) == triage_setup.n_test['bias']
        assert len(img_collection.files) == triage_setup.n_test['files']
        assert ('filter' in img_collection.keywords)
        assert ('flying monkeys' not in img_collection.keywords)
        assert len(img_collection.values('imagetyp', unique=True)) == 2

    def test_files_with_compressed(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir)
        assert len(collection._fits_files_in_directory(
            compressed=True)) == triage_setup.n_test['files']

    def test_files_with_no_compressed(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir)
        n_files_found = len(
            collection._fits_files_in_directory(compressed=False))
        n_uncompressed = (triage_setup.n_test['files'] -
                          triage_setup.n_test['compressed'])
        assert n_files_found == n_uncompressed

    def test_generator_full_path(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        for path, file_name in zip(collection._paths(), collection.files):
            assert path == os.path.join(triage_setup.test_dir, file_name)

    def test_hdus(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        n_hdus = 0
        for hdu in collection.hdus():
            assert isinstance(hdu, fits.PrimaryHDU)
            data = hdu.data  # must access the data to force scaling
            with pytest.raises(KeyError):
                hdu.header['bzero']
            n_hdus += 1
        assert n_hdus == triage_setup.n_test['files']

    def test_hdus_masking(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp', 'exposure'])
        old_data = np.array(collection.summary_info)
        for hdu in collection.hdus(imagetyp='bias'):
            pass
        new_data = np.array(collection.summary_info)
        assert (new_data == old_data).all()

    def test_headers(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        n_headers = 0
        for header in collection.headers():
            assert isinstance(header, fits.Header)
            assert ('bzero' in header)
            n_headers += 1
        assert n_headers == triage_setup.n_test['files']

    def test_headers_save_location(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        destination = mkdtemp()
        for header in collection.headers(save_location=destination):
            pass
        new_collection = \
            tff.ImageFileCollection(location=destination,
                                    keywords=['imagetyp'])
        basenames = lambda paths: set(
            [os.path.basename(file) for file in paths])

        assert (len(basenames(collection._paths()) -
                    basenames(new_collection._paths())) == 0)
        rmtree(destination)

    def test_headers_with_filter(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        cnt = 0
        for header in collection.headers(imagetyp='light'):
            assert header['imagetyp'].lower() == 'light'
            cnt += 1
        assert cnt == triage_setup.n_test['light']

    def test_headers_with_multiple_filters(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        cnt = 0
        for header in collection.headers(imagetyp='light',
                                         filter='R'):
            assert header['imagetyp'].lower() == 'light'
            assert header['filter'].lower() == 'r'
            cnt += 1
        assert cnt == (triage_setup.n_test['light'] -
                       triage_setup.n_test['need_filter'])

    def test_headers_with_filter_wildcard(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        cnt = 0
        for header in collection.headers(imagetyp='*'):
            cnt += 1
        assert cnt == triage_setup.n_test['files']

    def test_headers_with_filter_missing_keyword(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        for header in collection.headers(imagetyp='light',
                                         object=''):
            assert header['imagetyp'].lower() == 'light'
            with pytest.raises(KeyError):
                header['object']

    def test_generator_headers_save_with_name(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        for header in collection.headers(save_with_name='_new'):
            assert isinstance(header, fits.Header)
        new_collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                                 keywords=['imagetyp'])
        assert (len(new_collection._paths()) ==
                2 * (triage_setup.n_test['files']) -
                triage_setup.n_test['compressed'])
        print glob(triage_setup.test_dir + '/*_new*')
        [os.remove(fil) for fil in iglob(triage_setup.test_dir + '/*_new*')]
        print glob(triage_setup.test_dir + '/*_new*')

    def test_generator_data(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        for img in collection.data():
            assert isinstance(img, np.ndarray)

    def test_consecutive_fiilters(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp',
                                                       'filter',
                                                       'object'])
        no_files_match = collection.files_filtered(object='fdsafs')
        assert(len(no_files_match) == 0)
        some_files_should_match = collection.files_filtered(object=None,
                                                            imagetyp='light')
        print some_files_should_match
        assert(len(some_files_should_match) ==
               triage_setup.n_test['need_object'])

    def test_filter_does_not_not_permanently_change_file_mask(self,
                                                              triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        # ensure all files are originally unmasked
        assert(not collection.summary_info['file'].mask.any())
        # generate list that will match NO files
        collection.files_filtered(imagetyp='foisajfoisaj')
        # if the code works, this should have no permanent effect
        assert(not collection.summary_info['file'].mask.any())

    @pytest.mark.parametrize("new_keywords,collection_keys", [
                            (['imagetyp', 'object'], ['imagetyp', 'filter']),
                            (['imagetyp'], ['imagetyp', 'filter'])])
    def test_keyword_setting(self, new_keywords, collection_keys,
                             triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=collection_keys)
        tbl_orig = collection.summary_info
        collection.keywords = new_keywords
        tbl_new = collection.summary_info

        if set(new_keywords).issubset(collection_keys):
            # should just delete columns without rebuilding table
            assert(tbl_orig is tbl_new)
        else:
            # we need new keywords so must rebuild
            assert(tbl_orig is not tbl_new)

        for key in new_keywords:
            assert(key in tbl_new.keys())
        assert (tbl_orig['file'] == tbl_new['file']).all()
        assert (tbl_orig['imagetyp'] == tbl_new['imagetyp']).all()
        assert 'filter' not in tbl_new.keys()
        assert 'object' not in tbl_orig.keys()

    def test_keyword_setting_to_empty_list(self, triage_setup):
        ic = tff.ImageFileCollection(triage_setup.test_dir)
        ic.keywords = []
        assert ['file'] == ic.keywords

    def test_header_and_filename(self, triage_setup):
        collection = tff.ImageFileCollection(location=triage_setup.test_dir,
                                             keywords=['imagetyp'])
        for header, fname in collection.headers(return_fname=True):
            assert (fname in collection._paths())
            assert (isinstance(header, fits.Header))

    def test_dir_with_no_fits_files(self, tmpdir):
        empty_dir = tmpdir.mkdtemp()
        some_file = empty_dir.join('some_file.txt')
        some_file.dump('words')
        print empty_dir.listdir()
        collection = tff.ImageFileCollection(location=empty_dir.strpath,
                                             keywords=['imagetyp'])
        assert (collection.summary_info is None)
        for hdr in collection.headers():
            # this statement should not be reached if there are no FITS files
            assert 0

    def test_dir_with_no_keys(self, tmpdir, caplog):
        # This test should fail if the FITS files in the directory
        # are actually read.
        bad_dir = tmpdir.mkdtemp()
        not_really_fits = bad_dir.join('not_fits.fit')
        not_really_fits.dump('I am not really a FITS file')
        # make sure an error will be generated if the FITS file is read
        with pytest.raises(IOError):
            fits.getheader(not_really_fits.strpath)
        ic = tff.ImageFileCollection(location=bad_dir.strpath)
        # ImageFileCollection will suppress the IOError but log a warning
        # so check the log for the appropriate warning
        warnings = [rec for rec in caplog.records()
                    if ((rec.levelno == logging.WARN) &
                        ('Unable to get FITS header' in rec.message))]
        assert (len(warnings) == 0)

    def test_fits_summary_when_keywords_are_not_subset(self, triage_setup):
        """
        Catch case when there is overlap between keyword list
        passed to the ImageFileCollection and to files_filtered
        but the latter is not a subset of the former.
        """
        ic = tff.ImageFileCollection(triage_setup.test_dir,
                                     keywords=['imagetyp', 'exptime'])
        n_files = len(ic.files)
        files_missing_this_key = ic.files_filtered(imagetyp='*',
                                                   monkeys=None)
        assert(n_files > 0)
        assert(n_files == len(files_missing_this_key))

    def test_duplicate_keywords_in_setting(self, triage_setup):
        keywords_in = ['imagetyp', 'a', 'a']
        ic = tff.ImageFileCollection(triage_setup.test_dir,
                                     keywords=keywords_in)
        for key in set(keywords_in):
            assert (key in ic.keywords)
        # one keyword gets added: file
        assert len(ic.keywords) < len(keywords_in) + 1

    def test_keyword_includes_file(self, triage_setup):
        keywords_in = ['file', 'imagetyp']
        ic = tff.ImageFileCollection(triage_setup.test_dir,
                                     keywords=keywords_in)
        assert 'file' in ic.keywords
        file_keywords = [key for key in ic.keywords if key == 'file']
        assert len(file_keywords) == 1

    def test_setting_keywords_to_none(self, triage_setup):
        ic = tff.ImageFileCollection(triage_setup.test_dir,
                                     keywords=['imagetyp'])
        ic.keywords = None
        assert ic.summary_info == []

    def test_getting_value_for_keyword(self, triage_setup):
        ic = tff.ImageFileCollection(triage_setup.test_dir,
                                     keywords=['imagetyp'])
        # Does it fail if the keyword is not in the summary?
        with pytest.raises(ValueError):
            ic.values('filter')
        # If I ask for unique values do I get them?
        values = ic.values('imagetyp', unique=True)
        print ic.summary_info['imagetyp']
        assert values == list(set(ic.summary_info['imagetyp']))
        assert len(values) < len(ic.summary_info['imagetyp'])
        # Does the list of non-unique values match the raw column?
        values = ic.values('imagetyp', unique=False)
        assert values == list(ic.summary_info['imagetyp'])
        # Does unique actually default to false?
        values2 = ic.values('imagetyp')
        assert values == values2

    def test_collection_when_one_file_not_fits(self, triage_setup):
        not_fits = 'foo.fit'
        path_bad = os.path.join(triage_setup.test_dir, not_fits)
        # create an empty file...
        with open(path_bad, 'w'):
            pass
        ic = tff.ImageFileCollection(triage_setup.test_dir,
                                     keywords=['imagetyp'])
        assert not_fits not in ic.summary_info['file']
        os.remove(path_bad)

    def test_data_type_mismatch_in_fits_keyword_values(self, tmpdir,
                                                       triage_setup):
        # If one keyword has an unexpected type, do we notice?
        img = np.uint16(np.arange(100))
        bad_filter = fits.PrimaryHDU(img)
        bad_filter.header['imagetyp'] = IRAF_image_type('light')
        bad_filter.header['filter'] = 15.0
        path_bad = os.path.join(triage_setup.test_dir, 'bad_filter.fit')
        bad_filter.writeto(path_bad)
        with pytest.raises(ValueError):
            tff.ImageFileCollection(triage_setup.test_dir, keywords=['filter'])
        os.remove(path_bad)

    def test_filter_by_numerical_value(self, triage_setup):
        ic = tff.ImageFileCollection(triage_setup.test_dir, keywords=['naxis'])
        should_be_zero = ic.files_filtered(naxis=2)
        assert len(should_be_zero) == 0
        should_not_be_zero = ic.files_filtered(naxis=1)
        assert len(should_not_be_zero) == triage_setup.n_test['files']

    def test_unknown_generator_type_raises_error(self, triage_setup):
        ic = tff.ImageFileCollection(triage_setup.test_dir, keywords=['naxis'])
        with pytest.raises(ValueError):
            for foo in ic._generator('not a real generator'):
                pass

    def test_setting_write_location_to_bad_dest_raises_error(self, tmpdir,
                                                             triage_setup):
        new_tmp = tmpdir.mkdtemp()
        os.chmod(new_tmp.strpath, stat.S_IREAD)
        ic = tff.ImageFileCollection(triage_setup.test_dir, keywords=['naxis'])
        with pytest.raises(IOError):
            for hdr in ic.headers(save_location=new_tmp.strpath):
                pass

    def test_initializing_from_table(self, triage_setup):
        keys = ['imagetyp', 'filter']
        ic = tff.ImageFileCollection(triage_setup.test_dir,
                                     keywords=keys)
        table = ic.summary_info
        table_path = os.path.join(triage_setup.test_dir, 'input_tbl.csv')
        nonsense = 'forks'
        table['imagetyp'][0] = nonsense
        table.write(table_path, format='ascii', delimiter=',')
        ic = tff.ImageFileCollection(location=None, info_file=table_path)
        # keywords can only have been set from saved table
        for key in keys:
            assert key in ic.keywords
        # no location, so should be no files
        assert len(ic.files) == 0
        # no location, so no way to iterate over files
        with pytest.raises(AttributeError):
            for h in ic.headers():
                #print h
                pass
        ic = tff.ImageFileCollection(location=triage_setup.test_dir,
                                     info_file=table_path)
        # we now have a location, so did we get files?
        assert len(ic.files) == len(table)
        # Is the summary table masked?
        assert ic.summary_info.masked
        # can I loop over headers?
        for h in ic.headers():
            assert isinstance(h, fits.Header)
        # Does ImageFileCollection summary contain values from table?
        assert nonsense in ic.summary_info['imagetyp']

    def test_initializing_from_table_file_that_does_not_exist(self,
                                                              triage_setup,
                                                              caplog):
        # Do we get a warning if we try reading a file that doesn't exist,
        # but where we can initialize from a directory?
        ic = tff.ImageFileCollection(location=triage_setup.test_dir,
                                     info_file='iufadsdhfasdifre')
        warnings = [rec for rec in caplog.records()
                    if ((rec.levelno == logging.WARN) &
                        ('Unable to open table file' in rec.message))]
        assert (len(warnings) == 1)
        # Do we raise an error if the table name is bad AND the location
        # is None?
        with pytest.raises(IOError):
            ic = tff.ImageFileCollection(location=None,
                                         info_file='iufadsdhfasdifre')
        # Do we raise an error if the table name is bad AND
        # the location is given but is bad?
        with pytest.raises(OSError):
            ic = tff.ImageFileCollection(location='dasifjoaurun',
                                         info_file='iufadsdhfasdifre')

    def test_initialization_with_no_keywords(self, triage_setup):
        ic = tff.ImageFileCollection(location=triage_setup.test_dir)
        # iteration below failed before bugfix...
        execs = 0
        for h in ic.headers():
            execs += 1
            print h
        assert not execs

    def check_all_keywords_in_collection(self, image_collection):
        lower_case_columns = [c.lower() for c in
                              image_collection.summary_info.colnames]
        for h in image_collection.headers():
            for k in h:
                assert k.lower() in lower_case_columns

    def test_tabulate_all_keywords(self, triage_setup):
        ic = tff.ImageFileCollection(location=triage_setup.test_dir,
                                     keywords='*')
        self.check_all_keywords_in_collection(ic)

    def test_summary_table_is_always_masked(self, triage_setup):
        # First, try grabbing all of the keywords
        ic = tff.ImageFileCollection(location=triage_setup.test_dir,
                                     keywords='*')
        assert ic.summary_info.masked
        # Now, try keywords that every file will have
        ic.keywords = ['bitpix']
        assert ic.summary_info.masked
        # What about keywords that include some that will surely be missing?
        ic.keywords = ['bitpix', 'dsafui']
        assert ic.summary_info.masked

    def test_case_of_keywords_respected(self, triage_setup):
        keywords_in = ['BitPix', 'instrume', 'NAXIS']
        ic = tff.ImageFileCollection(location=triage_setup.test_dir,
                                     keywords=keywords_in)
        for key in keywords_in:
            assert key in ic.summary_info.colnames

    def test_grabbing_all_keywords_and_specific_keywords(self, triage_setup):
        keyword_not_in_headers = 'OIdn89!@'
        ic = tff.ImageFileCollection(triage_setup.test_dir,
                                     keywords=['*', keyword_not_in_headers])
        assert keyword_not_in_headers in ic.summary_info.colnames
        self.check_all_keywords_in_collection(ic)

    def test_grabbing_all_keywords_excludes_empty_key(self, tmpdir):
        # This test needs the data directory from tests rather than the
        # files set up in triage_setup because one of the data files
        # includes an odd keyword ('') that is produced by MaxImDL.
        data_dir = py.path.local(get_data_dir())
        test_dir = tmpdir
        data_dir.copy(test_dir)
        ic = tff.ImageFileCollection(test_dir.strpath, keywords='*')
        print ic.summary_info.colnames
        assert 'col0' not in ic.summary_info.colnames
