from datetime import datetime
from io import StringIO
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import requests
import time

IMAGE_DIRECTORIES = ['30min', '3day']
AURORA_30_URL = 'http://services.swpc.noaa.gov/text/aurora-nowcast-map.txt'
AURORA_3_URL = 'http://services.swpc.noaa.gov/experimental/text/aurora-3day-map.txt'  # TODO: get real URL later
LOGFILE = 'errors.log'
SECONDS_IN_DAY = 86400


def directories_exist(dirs):
    """
    Given a directory name (string), creates it if it doesn't
    exist already.

    str -> None
    """
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
def get_forecast(url):
    """
    Given data URL, retrieves the array file for global
    forecasts from the swpc.noaa site, given in Plate Carrée.
    
    Extent:
    1024 values covering 0 to 360 degrees in longitude (0.32846715 deg/px)
    512 values covering -90 to 90 degrees in latitude (0.3515625 deg/px)
    
    Returns:
    array: pandas array of the forecast
    datetime: date & time of forecast
    
    str -> np.array, datetime
    """
        
    extent = (-180, 180, -90, 90)
    timestamp = None
    
    # Download dataset
    # We wrap it as a file-like object to pass it directly 
    data = requests.get(url).content.decode()
        
    # Get timestamp
    timestamp = None
    # Iterate on the string line-by-line
    for line in iter(data.splitlines()):
        if line.startswith('# Product Valid At:'):
            timestamp = datetime.strptime(line[-16:], '%Y-%m-%d %H:%M')

    # Get data grid, wrapping our string `data` into a file-like StringIO
    array = pd.read_csv(StringIO(data), comment='#', delimiter='\s+', header=None)
    
    # Validate that we're not sending garbage
    assert array.shape == (512, 1024)
    assert str(timestamp)[0:2] == '20'  # From '2017...'
    
    return array, timestamp

def aurora_cmap():
    """
    Return a colormap with aurora-like colors
    and transparency.
    
    None -> LinearSegmentedColormap
    """
    from matplotlib.colors import LinearSegmentedColormap
    stops = {'red': [(0.00, 0.1725, 0.1725),
                     (0.50, 0.1725, 0.1725),
                     (1.00, 0.8353, 0.8353)],

             'green': [(0.00, 0.9294, 0.9294),
                       (0.50, 0.9294, 0.9294),
                       (1.00, 0.8235, 0.8235)],

             'blue': [(0.00, 0.3843, 0.3843),
                      (0.50, 0.3843, 0.3843),
                      (1.00, 0.6549, 0.6549)],

             'alpha': [(0.00, 0.0, 0.0),
                       (0.50, 1.0, 1.0),
                       (1.00, 1.0, 1.0)]}

    return LinearSegmentedColormap('aurora', stops)

def save_image(array, timestamp, folder, imtype='jpg'):
    """
    Saves the aurora tabular data into a jpg, whose
    top-left pixel is `(0, 0, 0)`.
    
    Arguments:
    array:     the tabular data
    timestamp: timestam of the forecast for filename
    
    pd.Dataframe, datetime, str, (str) -> None
    """
    
    # Overwrite top-left pixel for transparency in STK
    array[0, 0] = 0
    filename = '{0}/ovation_{1}.{2}'.format(folder, timestamp.strftime('%Y-%M-%d-%H-%M'), imtype)
    DPI = 96
    
    plt.figure(figsize=(50, 25),
               frameon=False,
               dpi=DPI)
    plt.imshow(array, 
               interpolation='bicubic',
               cmap = aurora_cmap(),
               origin='lower')
    plt.axis('off')
    plt.xticks([]), plt.yticks([])
    plt.savefig(filename,
                transparent=True,
                bbox_inches='tight',
                pad_inches=-0.035,  # Get rid of small padding border
                dpi=DPI)
    
def is_older_than(filename, days=7):
    """
    Returns True if file was created or modified more than the number
    of `days` ago. Default: 7 days.
    
    str, (opt: int) -> bool
    """    
    now = time.time()
    cutoff = now - (days * SECONDS_IN_DAY)
    t = os.stat(filename)
    creation_time = t.st_ctime
    if creation_time < cutoff:
        return True
    else:
        return False
        
if __name__ == '__main__':
    # Make sure image directories exist
    directories_exist(IMAGE_DIRECTORIES)
    
    # Gather data
    try:
        array_30, timestamp_30 = get_forecast(url=AURORA_30_URL)  # 30-minute forecast
        # TODO: Uncomment when we get working 3-day forecast link
        # array_3, timestamp_3 = get_forecast(url=AURORA_3_URL)  # 3-day forecast
    # But log and error out if no Internet
    except:
        with open(LOGFILE, 'a') as f:
            f.write('Connection error on {}.\n'.format(datetime.now()))
        raise RuntimeError('I/O Error')
      
    # Create images
    # TODO: Refactor to `for dir in IMAGE_..:` when we get 3-day forecast URL
    save_image(array_30, timestamp_30, folder=IMAGE_DIRECTORIES[0])
    # save_image(array_30, timestamp_30, folder=IMAGE_DIRECTORIES[1])

    # Clean up old images
    for directory in IMAGE_DIRECTORIES:
        for file in os.listdir(directory):
            filename = directory + '/' + file
            if is_older_than(filename, days=7):
                os.remove(filename)
    
