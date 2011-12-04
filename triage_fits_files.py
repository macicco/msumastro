import fnmatch
import pyfits
from keyword_names import RA, Dec, Object
from os import listdir, path

IMAGETYPE = 'IMAGETYP'
IRAF = {'flat': 'FLAT',
        'light': 'LIGHT',
        'dark': 'DARK',
        'bias': 'BIAS'}

def triage_fits_files(dir='.'):
    """
    Check FITS files in a directory for deficient headers

    `dir` is the name of the directory to search for files; default is
    the current working directory.
    """
    files = listdir(dir)
    files = fnmatch.filter(files, '*.fit')

    file_info_to_keep = ('file name', 'image type')
    file_info = {}
    for to_keep in file_info_to_keep:
        file_info[to_keep] = []
    file_needs_filter = []
    file_needs_object = []
    for fitsfile in files:
        try:
            hdulist = pyfits.open(path.join(dir,fitsfile))
        except IOError:
            print "Unable to open file %s" % fitsfile
            continue
        header = hdulist[0].header
        image_type =  IRAF_image_type(header[IMAGETYPE])
        file_info['file name'].append(fitsfile)
        file_info['image type'].append(image_type)
        if needs_filter(image_type) and 'FILTER' not in header.keys():
            file_needs_filter.append(fitsfile)

        object_info_present = ((set(RA.names) |
                                set(Dec.names) |
                                set(Object.names)) &
                               (set(header.keys())))
        if image_type == IRAF['light'] and not object_info_present:
            file_needs_object.append(fitsfile)
            
    dir_info = {'files': file_info,
                'needs_filter': file_needs_filter,
                'needs_object': file_needs_object}
    return dir_info
    
def IRAF_image_type(image_type):
    """Convert MaximDL default image type names to IRAF

    `image_type` is the value of the FITS header keyword IMAGETYP.
    
    MaximDL default is, e.g. 'Bias Frame', which IRAF calls
    'BIAS'. Can safely be called with an IRAF-style image_type.
    """
    return image_type.split()[0].upper()

def needs_filter(image_type):
    """Determines whether this type of image needs a FILTER keyword.

    Returns True if image is Flat or Light, False otherwise.
    """
    if image_type in (IRAF['flat'], IRAF['light']):
        return True
    else:
        return False

     
     

    
