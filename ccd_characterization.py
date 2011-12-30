from numpy import array, zeros

def ccd_dark_current(bias, dark, gain=1.0, average_dark=False):
    """
    Calculate the average dark current given bias and dark frames.

    `bias` should be either a single bias array or a numpy array of arrays. A
    list will be combined before subtraction from the dark.
    `dark` should be either a single dark array or a numpy array of arrays. 
    `gain` is the gain of the CCD.
    `average_dark` should be `True` if the return value should be the
    average of the dark currents form the individual frames.
    
    Returns the current in electrons/pixel
    """
    if len(bias.shape) == 3:
        average_bias = bias.mean(axis=0)
    else:
        average_bias = bias

    if len(dark.shape) == 2:
        dark_array = array(dark)
    else:
        dark_array = dark

    working_dark = zeros(dark_array.shape[1:2])
    dark_current = zeros(dark_array.shape[0])
    for i in range(0,dark_array.shape[0]):
        working_dark = dark_array[i,:,:] - average_bias
        dark_current[i] = gain*working_dark.mean()

    if average_dark:
        dark_current = dark_current.mean()
    return dark_current

def ccd_bias(bias):
    """
    Calculate the mean and width of a gaussian fit to the bias
    histogram.

    `bias` is a numpy array.
    """
def ccd_gain(bias, flat):
    """
    Calculate CCD gain from pair of bias and pair of flat frames.

    `bias` is a tuple or list of two bias frames as arrays.

    `flat` is a tuple or list of tywo flat frams as arrays.

    `bias` and `flat` should have the same shape.

    Returns the gain, calculated using the formula on p. 73 of the
    *Handbook of CCD Astronomy* by Steve Howell.
    """

    if len(bias) != 2 or len(flat) != 2:
        raise ValueError('bias and flat must each be two element tuple or list')

    b1 = bias[0]
    b2 = bias[1]
    f1 = flat[0]
    f2 = flat[1]

    flat_diff = f1 - f2
    bias_diff = b1 - b2

    gain = (((f1.mean() + f2.mean()) - (b1.mean() + b2.mean())) /
            ((f1-f2).var() - (b1-b2).var()))
    return gain

    