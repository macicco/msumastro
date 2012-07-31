from ..patch_headers import *
from tempfile import mkdtemp
from os import path
from shutil import rmtree
import numpy as np
import pytest

test_tuple = (1,2,3.1415)
_test_dir = ''
def test_sexagesimal_string():
    assert sexagesimal_string(test_tuple) == '01:02:03.14'

def test_sexagesimal_string_with_sign():
    assert sexagesimal_string(test_tuple, sign=True) == '+01:02:03.14'

def test_sexagesimal_string_with_precision():
    assert sexagesimal_string(test_tuple, precision=3) == '01:02:03.142'

def test_sexagesimal_string_with_precision_and_sign():
    assert sexagesimal_string(test_tuple, sign=True, precision=3) == '+01:02:03.142'

def test_read_object_list():
    observer, objects = read_object_list(dir=_test_dir)
    assert len(objects) == 2
    assert objects[0] == 'ey uma'
    assert objects[1] == 'm101'
    assert observer == 'Ima Observer'
    
def test_history_bad_mode():
    with pytest.raises(ValueError):
        history(test_history_bad_mode, mode='not a mode')
        
def test_history_begin():
    hist = history(test_history_begin, mode='begin')
    assert hist.find('BEGIN')>0
    assert hist.endswith('+')
    
def test_history_end():
    hist = history(test_history_end, mode='end')
    assert hist.find('END')>0
    assert hist.endswith('-')
    
def test_history_function_name():
    hist = history(test_history_function_name, mode='begin')
    assert hist.find('test_history_function_name') > 0
    
def test_data_is_unmodified_by_patch_headers():
    """No changes should be made to the data."""
    new_ext = '_new'
    patch_headers(_test_dir,new_file_ext=new_ext)
    fname = path.join(_test_dir,'uint16')
    fname_new = fname+ new_ext
    orig = pyfits.open(fname+'.fit',
                       do_not_scale_image_data=True)
    modified = pyfits.open(fname_new+'.fit',
                           do_not_scale_image_data=True)
    assert np.all(orig[0].data == modified[0].data)

def test_data_is_unmodified_by_adding_object():
    new_ext = '_obj'
    patch_headers(_test_dir,new_file_ext=new_ext)
    add_object_info(_test_dir, new_file_ext=new_ext)
    fname = path.join(_test_dir,'uint16')
    fname_new = fname+ new_ext + new_ext
    orig = pyfits.open(fname+'.fit',
                       do_not_scale_image_data=True)
    modified = pyfits.open(fname_new+'.fit',
                           do_not_scale_image_data=True)
    assert np.all(orig[0].data == modified[0].data)

def test_adding_object_name():
    new_ext = '_obj_name_test'
    patch_headers(_test_dir, new_file_ext=new_ext)
    add_object_info(_test_dir, new_file_ext=new_ext)
    fname = path.join(_test_dir,'uint16')
    fname += new_ext + new_ext
    with_name = pyfits.open(fname+'.fit')
    print 'add object name: %s' % fname
    assert (with_name[0].header['object'] == 'm101')
    
def setup():
    global _test_dir
    from shutil import copy

    _test_dir = mkdtemp()
    to_write = '# comment 1\nIma Observer\n# comment 2\ney uma\nm101'
    object_file = open(path.join(_test_dir,'obsinfo.txt'),'wb')
    object_file.write(to_write)
    copy(path.join('data', 'uint16.fit'), _test_dir)

def teardown():
    global _test_dir
    rmtree(_test_dir)
