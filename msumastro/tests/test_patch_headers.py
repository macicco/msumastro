from os import path, chdir, getcwd, remove
from shutil import rmtree, copy, move
from tempfile import mkdtemp
from glob import glob
import warnings
import logging

import pytest
pytest_plugins = "capturelog"
import numpy as np
from numpy.testing import assert_almost_equal
from astropy.io import fits
from astropy.coordinates import Angle, FK5Coordinates
from astropy import units as u

#from ..patch_headers import *
from .. import patch_headers as ph
from ..feder import Feder, FederSite, ApogeeAltaU9
from utilities import make_overscan_test_files

test_tuple = (1, 2, 3.1415)
_test_dir = ''
_default_object_file_name = 'obsinfo.txt'
_test_image_name = 'uint16.fit'


def test_sexagesimal_string():
    assert ph.sexagesimal_string(test_tuple) == '01:02:03.14'


def test_sexagesimal_string_with_sign():
    assert ph.sexagesimal_string(test_tuple, sign=True) == '+01:02:03.14'


def test_sexagesimal_string_with_precision():
    assert ph.sexagesimal_string(test_tuple, precision=3) == '01:02:03.142'


def test_sexagesimal_string_with_precision_and_sign():
    assert (ph.sexagesimal_string(test_tuple, sign=True, precision=3) ==
            '+01:02:03.142')


@pytest.mark.usefixtures('object_file_no_ra')
def test_read_object_list():
    objects, RA, Dec = ph.read_object_list(dir=_test_dir)
    assert len(objects) == 2
    assert objects[0] == 'ey uma'
    assert objects[1] == 'm101'


def test_history_bad_mode():
    with pytest.raises(ValueError):
        ph.history(test_history_bad_mode, mode='not a mode')


def test_history_begin():
    hist = ph.history(test_history_begin, mode='begin')
    assert hist.find('BEGIN') > 0
    assert hist.endswith('+')


def test_history_end():
    hist = ph.history(test_history_end, mode='end')
    assert hist.find('END') > 0
    assert hist.endswith('-')


def test_history_function_name():
    hist = ph.history(test_history_function_name, mode='begin')
    assert hist.find('test_history_function_name') > 0


def test_data_is_unmodified_by_patch_headers():
    """No changes should be made to the data."""
    new_ext = '_new'
    ph.patch_headers(_test_dir, new_file_ext=new_ext)
    fname = path.join(_test_dir, 'uint16')
    fname_new = fname + new_ext
    orig = fits.open(fname + '.fit',
                     do_not_scale_image_data=True)
    modified = fits.open(fname_new + '.fit',
                         do_not_scale_image_data=True)
    assert np.all(orig[0].data == modified[0].data)


def test_data_is_unmodified_by_adding_object():
    new_ext = '_obj'
    ph.patch_headers(_test_dir, new_file_ext=new_ext)
    ph.add_object_info(_test_dir, new_file_ext=new_ext)
    fname = path.join(_test_dir, 'uint16')
    fname_new = fname + new_ext + new_ext
    orig = fits.open(fname + '.fit',
                     do_not_scale_image_data=True)
    modified = fits.open(fname_new + '.fit',
                         do_not_scale_image_data=True)
    assert np.all(orig[0].data == modified[0].data)


def test_adding_object_name(use_list=None,
                            use_obj_dir=None,
                            check_fits_file='uint16'):
    """
    Test adding object name

    Provide `use_list` to override the default object file name.
    Provide `use_obj_dir` to specify directory in which the object file
    is found. Defaults to directory in which the images reside if
    `use_obj_dir` is None.
    """
    new_ext = '_obj_name_test'
    ph.patch_headers(_test_dir, new_file_ext=new_ext)
    ph.add_object_info(_test_dir, new_file_ext=new_ext,
                       object_list=use_list, object_list_dir=use_obj_dir)
    fname = path.join(_test_dir, check_fits_file)
    fname += new_ext + new_ext
    with_name = fits.open(fname + '.fit')
    print 'add object name: %s' % fname
    assert (with_name[0].header['object'] == 'm101')
    return with_name


def test_adding_object_name_using_last_object():
    copy(path.join(_test_dir, 'uint16.fit'),
         path.join(_test_dir, 'uint16_2.fit'))
    test_adding_object_name(check_fits_file='uint16')
    test_adding_object_name(check_fits_file='uint16_2')


def test_writing_patched_files_to_directory():
    files = glob(path.join(_test_dir, '*.fit*'))
    n_files_init = len(glob(path.join(_test_dir, '*.fit*')))
    dest_dir = mkdtemp()
    ph.patch_headers(_test_dir, new_file_ext=None, save_location=dest_dir)
    print files
    n_files_after = len(glob(path.join(_test_dir, '*.fit*')))
    print n_files_after
    n_files_destination = len(glob(path.join(dest_dir, '*.fit*')))
    print dest_dir
    rmtree(dest_dir)
    assert ((n_files_init == n_files_after) &
            (n_files_init == n_files_destination))


def test_adding_object_name_to_different_directory(use_list=None,
                                                   use_obj_dir=None):
    new_ext = '_obj_name_test'
    ph.patch_headers(_test_dir, new_file_ext=new_ext)
    destination_dir = mkdtemp()
    ph.add_object_info(_test_dir, new_file_ext=new_ext,
                       save_location=destination_dir,
                       object_list=use_list, object_list_dir=use_obj_dir)
    fname = path.join(destination_dir, 'uint16')
    fname += new_ext + new_ext
    with_name = fits.open(fname + '.fit')
    print 'add object name: %s' % fname
    assert (with_name[0].header['object'] == 'm101')
    return with_name


def test_purging_maximdl5_keywords():

    feder = Feder()
    mdl5_name = 'maximdl5_header.fit'
    copy(path.join('data', mdl5_name), _test_dir)
    hdr5 = fits.getheader(path.join(_test_dir, mdl5_name))
    ph.purge_bad_keywords(hdr5, history=True, force=False)
    for software in feder.software:
        if software.created_this(hdr5[software.fits_keyword]):
            break
    keyword_present = False
    for keyword in software.bad_keywords:
        keyword_present = (keyword_present or (keyword in hdr5))
    assert not keyword_present


def test_adding_overscan_apogee_u9():
    original_dir = getcwd()

    apogee = ApogeeAltaU9()
    print getcwd()
    oscan_dir, has_oscan, has_no_oscan = make_overscan_test_files(_test_dir)
    print getcwd()

    chdir(path.join(_test_dir, oscan_dir))
    ph.patch_headers(dir='.', new_file_ext='', overwrite=True, purge_bad=False,
                     add_time=False, add_apparent_pos=False,
                     add_overscan=True, fix_imagetype=False)
    print _test_dir
    header_no_oscan = fits.getheader(has_no_oscan)
    assert not header_no_oscan['oscan']
    header_yes_oscan = fits.getheader(has_oscan)
    assert header_yes_oscan['oscan']
    assert header_yes_oscan['oscanax'] == apogee.overscan_axis
    assert header_yes_oscan['oscanst'] == apogee.overscan_start
    print getcwd()
    chdir(original_dir)
    print getcwd()
    assert (True)


def test_fix_imagetype():
    imagetypes_to_check = {'Bias Frame': 'BIAS',
                           'Dark Frame': 'DARK',
                           'Light Frame': 'LIGHT',
                           'Flat Frame': 'FLAT'}
    for im_type in imagetypes_to_check:
        header = fits.Header()

        header['imagetyp'] = im_type
        # first run SHOULD change imagetyp
        print header
        ph.change_imagetype_to_IRAF(header, history=False)
        assert(header['imagetyp'] == imagetypes_to_check[im_type])
        # second call should NOT change imagetyp
        print header
        ph.change_imagetype_to_IRAF(header, history=True)
        assert(header['imagetyp'] == imagetypes_to_check[im_type])
        with pytest.raises(KeyError):
            print header['history']
        # change imagetype back to non-IRAF
        header['imagetyp'] = im_type
        # change with history
        ph.change_imagetype_to_IRAF(header, history=True)
        assert('history' in header)


def test_add_object_name_uses_object_list_name():

    custom_object_name = 'my_object_list.txt'
    old_object_path = path.join(_test_dir, _default_object_file_name)
    new_path = path.join(_test_dir, custom_object_name)
    move(old_object_path, new_path)
    fits_with_obj_name = test_adding_object_name(use_list=custom_object_name)
    # The line below is probably not really necessary since the same test
    # is done in test_adding_object_name but it doesn't hurt to test it
    # here too
    assert (fits_with_obj_name[0].header['object'] == 'm101')


def test_add_object_name_with_custom_dir_standard_name():

    a_temp_dir = mkdtemp()

    old_object_path = path.join(_test_dir, _default_object_file_name)
    new_path = path.join(a_temp_dir, _default_object_file_name)
    move(old_object_path, new_path)
    test_adding_object_name(use_obj_dir=a_temp_dir)


def test_add_object_name_uses_object_list_dir():

    a_temp_dir = mkdtemp()

    custom_object_name = 'my_object_list.txt'
    old_object_path = path.join(_test_dir, _default_object_file_name)
    new_path = path.join(a_temp_dir, custom_object_name)
    move(old_object_path, new_path)
    # first make sure object name isn't added if object list can't be found
    with pytest.raises(IOError):
        test_adding_object_name(use_list=custom_object_name)

    # Now make sure it works when we specify the directory; need to redo
    # setup to clear out files made in pass above
    setup_function(test_add_object_name_uses_object_list_dir)
    test_adding_object_name(use_list=custom_object_name,
                            use_obj_dir=a_temp_dir)


def test_read_object_list_with_ra_dec():
    temp_dir = mkdtemp()
    obj_name = 'objects_with_ra.txt'
    object_path = path.join(temp_dir, obj_name)
    object_in = 'ey uma'
    RA_in = "09:02:20.76"
    Dec_in = "+49:49:09.3"
    to_write = 'object, RA, Dec\n{},{},{}'.format(object_in, RA_in, Dec_in)
    object_file = open(object_path, 'wb')
    object_file.write(to_write)
    object_file.close()
    obj, RA, Dec = ph.read_object_list(temp_dir, obj_name)
    assert(obj[0] == object_in)
    assert(RA[0] == RA_in)
    assert(Dec[0] == Dec_in)


def get_patch_header_warnings(log):
    patch_header_warnings = []
    for record in log.records():
        if (('patch_headers' in record.name) and (record.levelno ==
                                                  logging.WARN)):

            patch_header_warnings.append(record.message)

    patch_headers_message_text = '\n'.join(patch_header_warnings)
    return patch_headers_message_text


def test_missing_object_file_issues_warning(caplog):
    remove(path.join(_test_dir, _default_object_file_name))
    ph.add_object_info(_test_dir)
    patch_header_warnings = get_patch_header_warnings(caplog)
    assert 'No object list in directory' in patch_header_warnings


def test_no_object_match_for_image_warning_includes_file_name(caplog):
    remove(path.join(_test_dir, _default_object_file_name))
    to_write = '# comment 1\n# comment 2\nobject\nsz lyn'
    object_file = open(path.join(_test_dir, _default_object_file_name), 'wb')
    object_file.write(to_write)
    object_file.close()
    ph.patch_headers(_test_dir, new_file_ext=None, overwrite=True)
    ph.add_object_info(_test_dir)
    patch_header_warnings = get_patch_header_warnings(caplog)
    assert 'No object found' in patch_header_warnings
    assert _test_image_name in patch_header_warnings


def test_add_ra_dec_from_object_name():
    full_path = path.join(_test_dir, _test_image_name)
    f = fits.open(full_path, do_not_scale_image_data=True)
    h = f[0].header
    del h['OBJCTRA']
    del h['OBJCTDEC']
    h['OBJECT'] = 'M101'
    with warnings.catch_warnings():
        ignore_from = 'astropy.io.fits.hdu.hdulist'
        warnings.filterwarnings('ignore', module=ignore_from)
        f.writeto(full_path, clobber=True)
    f.close()
    ph.add_ra_dec_from_object_name(_test_dir, new_file_ext=None)
    f = fits.open(full_path, do_not_scale_image_data=True)
    h = f[0].header
    m101_ra_dec_correct = FK5Coordinates('14h03m12.58s +54d20m55.50s')
    header_m101 = FK5Coordinates(ra=h['ra'], dec=h['dec'],
                                 unit=(u.hour, u.degree))

    assert_almost_equal(m101_ra_dec_correct.ra.hours,
                        header_m101.ra.hours)
    assert_almost_equal(m101_ra_dec_correct.dec.degrees,
                        header_m101.dec.degrees)


def test_times_apparent_pos_added():
    # the correct value below is from the USNO JD calculator using the UT
    # of the start of the observation in the file uint16.fit, which is
    # 2012-06-05T04:17:00
    JD_correct = 2456083.678472222
    # The "correct" values below are from converting the RA/Dec in uint16 to
    # decimal hours/degrees
    RA_correct = 14.054166667  # hours
    Dec_correct = 54.351111111  # degrees

    # Get the "correct" LST from astropysics and assume that that is correct
    f = FederSite()
    f.currentobsjd = JD_correct
    LST_astropysics = f.localSiderialTime()

    HA_correct = LST_astropysics - RA_correct

    ph.patch_headers(_test_dir, new_file_ext=None, overwrite=True)
    header = fits.getheader(path.join(_test_dir, _test_image_name))

    # check Julian Date
    assert_almost_equal(header['JD-OBS'], JD_correct)

    # calculate then check LST
    h, m, s = header['LST'].split(':')
    header_lst = int(h) + int(m)/60. + float(s)/3600.

    assert_almost_equal(header_lst, LST_astropysics, decimal=5)

    # calculate then check HA
    h, m, s = header['HA'].split(':')
    header_HA = int(h) + int(m)/60. + float(s)/3600.

    assert_almost_equal(HA_correct, header_HA)

    # calculate, then check, altitude
    latitude = f.latitude.radians
    Dec_a = Angle(Dec_correct, unit=u.degree)
    HA_a = Angle(HA_correct, unit=u.hour)
    sin_alt = (np.sin(latitude) * np.sin(Dec_a.radians) +
               (np.cos(latitude) * np.cos(Dec_a.radians) *
                np.cos(HA_a.radians)))
    alt = Angle(np.arcsin(sin_alt), unit=u.radian)
    header_alt = header['alt-obj']
    assert_almost_equal(alt.degrees, header_alt, decimal=5)

    # calculate, then check, airmass
    zenith_angle = Angle(90 - alt.degrees, unit=u.degree)
    airmass_correct = 1/np.cos(zenith_angle.radians)
    assert_almost_equal(airmass_correct, header['airmass'], decimal=3)


@pytest.fixture(params=['object', 'OBJECT', 'Object'])
def object_file_no_ra(request):
    to_write = '# comment 1\n# comment 2\n' + request.param + '\ney uma\nm101'
    object_file = open(path.join(_test_dir, _default_object_file_name), 'wb')
    object_file.write(to_write)
    object_file.close()


def setup_function(function):
    global _test_dir
    global _test_image_name

    _test_dir = mkdtemp()
    to_write = '# comment 1\n# comment 2\nobject\ney uma\nm101'
    object_file = open(path.join(_test_dir, _default_object_file_name), 'wb')
    object_file.write(to_write)
    object_file.close()
    copy(path.join('data', _test_image_name), _test_dir)


def teardown_function(function):
    global _test_dir
    rmtree(_test_dir)