from .. import image_collection as tff
from ..patch_headers import IRAF_image_type
import os
import numpy
import astropy.io.fits as fits
from shutil import rmtree
import gzip
from tempfile import mkdtemp
import numpy as np
import pytest

_n_test = {'files': 0, 'need_object': 0,
           'need_filter': 0, 'bias': 0,
           'compressed': 0, 'light': 0,
           'need_pointing': 0}

_test_dir = ''
_filters = []
_original_dir = ''


def test_fits_summary():
    keywords = ['imagetyp', 'filter']
    image_collection = tff.ImageFileCollection(_test_dir,
                                               keywords=keywords)
    summary = image_collection.fits_summary(keywords=keywords)
    print summary['file']
    print summary.keys()
    assert len(summary['file']) == _n_test['files']
    for keyword in keywords:
        assert len(summary[keyword]) == _n_test['files']
    # explicit conversion to array is needed to avoid astropy Table bug in
    # 0.2.4
    print np.array(summary['file'] == 'no_filter_no_object_bias.fit')
    # print summary['filter'][summary['file'] ==
    # 'no_filter_no_object_bias.fit']
    assert summary['filter'][
        summary['file'] == 'no_filter_no_object_bias.fit'] == ['']


class TestImageFileCollection(object):

    def test_storage_dir_set(self):
        try:
            should_work = tff.ImageFileCollection(location=_test_dir,
                                                  storage_dir=_test_dir)
            assert True
        except OSError:
            assert False

        with pytest.raises(OSError):
            tff.ImageFileCollection(location=_test_dir, storage_dir='/')

        img_collection = tff.ImageFileCollection(
            location=_test_dir, keywords=['imagetyp', 'filter'])
        print img_collection.files_filtered(imagetyp='bias')
        print _n_test
        assert len(img_collection.files_filtered(
            imagetyp='bias')) == _n_test['bias']
        assert len(img_collection.files) == _n_test['files']
        assert img_collection.has_key('filter')
        assert not img_collection.has_key('flying monkeys')
        assert len(img_collection.values('imagetyp', unique=True)) == 2

    def test_files_with_compressed(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        assert len(collection._fits_files_in_directory(
            compressed=True)) == _n_test['files']

    def test_files_with_no_compressed(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        n_files_found = len(
            collection._fits_files_in_directory(compressed=False))
        n_uncompressed = _n_test['files'] - _n_test['compressed']
        assert n_files_found == n_uncompressed

    def test_generator_full_path(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        for path, file_name in zip(collection.paths(), collection.files):
            assert path == os.path.join(_test_dir, file_name)

    def test_hdus(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        n_hdus = 0
        for hdu in collection.hdus():
            assert isinstance(hdu, fits.PrimaryHDU)
            data = hdu.data  # must access the data to force scaling
            with pytest.raises(KeyError):
                hdu.header['bzero']
            n_hdus += 1
        assert n_hdus == _n_test['files']

    def test_hdus_masking(self):
        collection = tff.ImageFileCollection(location=_test_dir,
                                             keywords=['imagetyp', 'exposure'])
        old_data = np.array(collection.summary_info)
        for hdu in collection.hdus(imagetyp='bias'):
            pass
        new_data = np.array(collection.summary_info)
        assert (new_data == old_data).all()

    def test_headers(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        n_headers = 0
        for header in collection.headers():
            assert isinstance(header, fits.Header)
            assert ('bzero' in header)
            n_headers += 1
        assert n_headers == _n_test['files']

    def test_headers_save_location(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        destination = mkdtemp()
        for header in collection.headers(save_location=destination):
            pass
        new_collection = tff.ImageFileCollection(location=
                                                 destination)
        basenames = lambda paths: set(
            [os.path.basename(file) for file in paths])

        assert (len(basenames(collection.paths()) -
                    basenames(new_collection.paths())) == 0)
                #_n_test['compressed'])
        rmtree(destination)

    def test_headers_with_filter(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        cnt = 0
        for header in collection.headers(imagetyp='light'):
            assert header['imagetyp'].lower() == 'light'
            cnt += 1
        assert cnt == _n_test['light']

    def test_headers_with_multiple_filters(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        cnt = 0
        for header in collection.headers(imagetyp='light',
                                         filter='R'):
            assert header['imagetyp'].lower() == 'light'
            assert header['filter'].lower() == 'r'
            cnt += 1
        assert cnt == _n_test['light'] - _n_test['need_filter']

    def test_headers_with_filter_wildcard(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        cnt = 0
        for header in collection.headers(imagetyp='*'):
            cnt += 1
        assert cnt == _n_test['files']

    def test_headers_with_filter_missing_keyword(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        for header in collection.headers(imagetyp='light',
                                         object=''):
            assert header['imagetyp'].lower() == 'light'
            with pytest.raises(KeyError):
                header['object']

    def test_generator_headers_save_with_name(self):
        from glob import iglob, glob
        collection = tff.ImageFileCollection(location=_test_dir)
        for header in collection.headers(save_with_name='_new'):
            assert isinstance(header, fits.Header)
        new_collection = tff.ImageFileCollection(location=_test_dir)
        assert (len(new_collection.paths()) ==
                2 * (_n_test['files']) - _n_test['compressed'])
        print glob(_test_dir + '/*_new*')
        [os.remove(fil) for fil in iglob(_test_dir + '/*_new*')]
        print glob(_test_dir + '/*_new*')

    def test_generator_data(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        for img in collection.data():
            assert isinstance(img, np.ndarray)

    def test_missing_value_in_summary(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        with pytest.raises(ValueError):
            collection.fits_summary(missing='string')

    def test_consecutive_fiilters(self):
        collection = tff.ImageFileCollection(location=_test_dir,
                                             keywords=['imagetyp',
                                                       'filter',
                                                       'object'])
        no_files_match = collection.files_filtered(object='fdsafs')
        assert(len(no_files_match) == 0)
        some_files_should_match = collection.files_filtered(object='',
                                                            imagetyp='light')
        print some_files_should_match
        assert(len(some_files_should_match) == _n_test['need_object'])

    def test_keyword_setting(self):
        collection = tff.ImageFileCollection(location=_test_dir,
                                             keywords=['imagetyp', 'filter'])
        tbl_orig = collection.summary_info
        collection.keywords = ['imagetyp', 'object']
        tbl_new = collection.summary_info
        assert (tbl_orig['file'] == tbl_new['file']).all()
        assert (tbl_orig['imagetyp'] == tbl_new['imagetyp']).all()
        assert 'filter' not in tbl_new.keys()
        assert 'object' not in tbl_orig.keys()

    def test_header_and_filename(self):
        collection = tff.ImageFileCollection(location=_test_dir)
        for header, fname in collection.headers(return_fname=True):
            assert (fname in collection.paths())
            assert (isinstance(header, fits.Header))


def setup_module():
    global _n_test
    global _test_dir
    global _original_dir

    for key in _n_test.keys():
        _n_test[key] = 0

    _test_dir = mkdtemp()
    _original_dir = os.getcwd()

    os.chdir(_test_dir)
    img = numpy.uint16(numpy.arange(100))

    no_filter_no_object = fits.PrimaryHDU(img)
    no_filter_no_object.header['imagetyp'] = IRAF_image_type('light')
    no_filter_no_object.writeto('no_filter_no_object_light.fit')
    _n_test['files'] += 1
    _n_test['need_object'] += 1
    _n_test['need_filter'] += 1
    _n_test['light'] += 1
    _n_test['need_pointing'] += 1

    no_filter_no_object.header['imagetyp'] = IRAF_image_type('bias')
    no_filter_no_object.writeto('no_filter_no_object_bias.fit')
    _n_test['files'] += 1
    _n_test['bias'] += 1

    filter_no_object = fits.PrimaryHDU(img)
    filter_no_object.header['imagetyp'] = IRAF_image_type('light')
    filter_no_object.header['filter'] = 'R'
    filter_no_object.writeto('filter_no_object_light.fit')
    _n_test['files'] += 1
    _n_test['need_object'] += 1
    _n_test['light'] += 1
    _n_test['need_pointing'] += 1

    filter_no_object.header['imagetyp'] = IRAF_image_type('bias')
    filter_no_object.writeto('filter_no_object_bias.fit')
    _n_test['files'] += 1
    _n_test['bias'] += 1

    filter_object = fits.PrimaryHDU(img)
    filter_object.header['imagetyp'] = IRAF_image_type('light')
    filter_object.header['filter'] = 'R'
    filter_object.header['OBJCTRA'] = '00:00:00'
    filter_object.header['OBJCTDEC'] = '00:00:00'
    filter_object.writeto('filter_object_light.fit')
    _n_test['files'] += 1
    _n_test['light'] += 1
    _n_test['need_object'] += 1
    filter_file = open('filter_object_light.fit', 'rb')
    fzipped = gzip.open('filter_object_light.fit.gz', 'wb')
    fzipped.writelines(filter_file)
    fzipped.close()
    _n_test['files'] += 1
    _n_test['compressed'] += 1
    _n_test['light'] += 1
    _n_test['need_object'] += 1


def teardown_module():
    global _n_test

    for key in _n_test.keys():
        _n_test[key] = 0
    rmtree(_test_dir)
    os.chdir(_original_dir)