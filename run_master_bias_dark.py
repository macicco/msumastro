import triage_fits_files as tff
import ccd_characterization as ccd_char
from astropysics import ccd
from os import path
from numpy import median, mean
from datetime import datetime
from pyfits import Header
import pyfits

temperature_tolerance = 1 #degree C
combiner = ccd.ImageCombiner()

def combine_from_list(dir, fnames, combiner):
    data = []
    for fn in fnames:
        a_data = ccd.FitsImage(path.join(dir,fn))
        data.append(a_data)
    return combiner.combineImages(data)

def master_frame(data, img_type, T, Terr, sample=None,combiner=None):
    copy_from_sample = ['xbinning', 'ybinning',
                        'xpixsz', 'ypixsz', 'exptime']
    img = ccd.FitsImage(data)
    hdr = img.fitsfile[0].header
    hdr.update('imagetyp',img_type)
    now = datetime.utcnow()
    now = now.replace(microsecond=0)
    hdr.update('date', now.isoformat(),
               'Creation date of file')
    hdr.update('ccd-temp', T, 'Average temperature of CCD')
    hdr.update('temp-dev', Terr,
               'Standard deviation of CCD temperature')
    if combiner is not None:
        hdr.update('cmbn-mth',combiner.method,
                   'Combination method for producing master')
        
    if sample is not None:
        if not isinstance(sample, Header):
            raise TypeError
        cards = sample.ascard
        for key in copy_from_sample:
            hdr.update(key,cards[key].value,cards[key].comment)
    return img

def add_files_info(fits_image, files):
    hdr = fits_image.fitsfile[0].header
    hdr.update('n-files',len(files),
               'Number of files combined to make master')
    hdr.add_comment('This master produced by combining the files below:')
    for fil in files:
        hdr.add_comment('    '+fil)
    
for currentDir in foo:
    keywords = ['imagetyp', 'exptime', 'ccd-temp']
    images = tff.ImageFileCollection(location=currentDir,
                                     keywords=keywords)
    useful = images.summary_info
    #print useful.data
    bias_files=useful.where(useful['imagetyp']=='BIAS')
    if bias_files:
        combiner.method = 'median'
        master_bias = combine_from_list(currentDir,
                                        bias_files['file'], combiner)
        avg_temp = bias_files['ccd-temp'].mean()
        temp_dev = bias_files['ccd-temp'].std()
        sample = pyfits.open(path.join(currentDir,bias_files['file'][0]))
        bias_im = master_frame(master_bias, 'MASTER BIAS', avg_temp,
                               temp_dev, sample=sample[0].header,
                               combiner=combiner)
        add_files_info(bias_im,bias_files['file'])
        bias_im.save(path.join(currentDir, 'Master_Bias.fit'))
        
    dark_files = useful.where(useful['imagetyp']=='DARK')
    if dark_files:
        exposure_times = set(dark_files['exptime'])
        master_dark = {}
        avg_temp = {}
        for time in exposure_times:
            these_darks=dark_files.where(dark_files['exptime']==time)
            avg_temp[time] = these_darks['ccd-temp'].mean()
            temp_dev = these_darks['ccd-temp'].std()
            good_darks = abs(these_darks['ccd-temp'] - avg_temp[time]) < temperature_tolerance
            if not good_darks.all():
                raise RuntimeError('Darks with exposure time %f have a temperature problem!' % time )
            combiner.method = 'median'
            master_dark = combine_from_list(currentDir,
                                            these_darks['file'], combiner)
            sample = pyfits.open(path.join(currentDir,these_darks['file'][0]))
            dark_im = master_frame(master_dark, 'MASTER DARK', avg_temp[time],
                                   temp_dev, sample=sample[0].header,
                                   combiner=combiner)
            dark_fn = 'Master_Dark_{:.2f}_sec_{:.2f}_degC.fit'.format(round(time, 2),
                                                          round(avg_temp[time], 2))
            add_files_info(dark_im,these_darks['file'])
            dark_im.save(path.join(currentDir, dark_fn))

            print time, avg_temp[time], median(master_dark[time]), mean(master_dark[time])
#            print ccd_char.ccd_dark_current(master_bias,dark_data,gain=1.5)/time

            