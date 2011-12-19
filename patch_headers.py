from feder import feder
import pyfits
#from coatpy import Sesame
import asciitable
import os
from keyword_names import *
from astropysics import obstools, coords
from math import cos, pi

def parse_dateobs(dateobs):
    date, time = dateobs.split('T')
    date = date.split('-')
    date = map(int, date)
    time = map(int, time.split(':'))
    date.extend(time)
    return date
    
def sexagesimal_string(dms, precision=2, sign=False):
    """Convert degrees, minutes, seconds into a string

    dms should be a list or tuple of (degrees or hours, minutes, seconds)
    precision is the number of digits to be kept to the right of the
    decimal in the seconds (default is 2)
    sign should be True if a leading sign should be displayed for
    positive values.
    """
    if sign:
        degree_format = '{0[0]:+03}'
    else:
        degree_format = '{0[0]:02}'

    seconds_width = str(precision + 3)
    format_string = degree_format+':{0[1]:02}:{0[2]:0'+seconds_width+'.'+str(precision)+'f}'
    return format_string.format(dms)

def deg2dms(dd):
    """Convert decimal degrees to degrees, minutes, seconds.

    Poached from stackoverflow.
    """
    mnt,sec = divmod(dd*3600,60)
    deg,mnt = divmod(mnt,60)
    return int(deg),int(mnt),sec
    
def patch_headers(dir='.',manifest='Manifest.txt'):
    try:
        image_info_file = open(os.path.join(dir, manifest))
    except IOError:
        raise

    image_info = asciitable.read(image_info_file)
    image_info_file.close()
    current_dir = os.getcwd()
    os.chdir(dir)

    files = image_info['file name']

    latitude.value = sexagesimal_string(feder.latitude.dms)
    longitude.value = sexagesimal_string(feder.longitude.dms)
    obs_altitude.value = feder.altitude
    
    for image in files:
        hdulist = pyfits.open(image)
        header = hdulist[0].header
        int16 = (header['bitpix'] == 16)
        hdulist.verify('fix')
        dateobs = parse_dateobs(header['date-obs'])
        JD.value = round(obstools.calendar_to_jd(dateobs), 6)
        MJD.value = round(obstools.calendar_to_jd(dateobs, mjd=True), 6)
        
        # setting currentobsjd makes calls following it use that time
        # for calculations
        feder.currentobsjd = JD.value
        LST.value = feder.localSiderialTime()
        LST.value = sexagesimal_string(deg2dms(LST.value))
        
        for keyword in all_files:
            keyword.add_to_header(hdulist[0])
        if header['imagetyp'] == 'LIGHT':
            RA.set_value_from_header(header)
            Dec.set_value_from_header(header)
            RA.value = RA.value.replace(' ',':')
            Dec.value = Dec.value.replace(' ',':')
            object_coords = coords.EquatorialCoordinatesEquinox((RA.value, Dec.value))
            alt_az = feder.apparentCoordinates(object_coords, refraction=False)
            altitude.value = round(alt_az.alt.d, 5)
            azimuth.value = round(alt_az.az.d, 5)
            airmass.value = round(1/cos(pi/2 - alt_az.alt.r),3)
            hour_angle.value = sexagesimal_string(
                                coords.EquatorialCoordinatesEquinox((feder.localSiderialTime()-
                                                                     object_coords.ra.hours,
                                                                     0)).ra.hms)
            for keyword in light_files:
                if keyword.value is not None:
                    keyword.add_to_header(hdulist[0])
                
        hdulist.writeto(image+'new')
    
    
