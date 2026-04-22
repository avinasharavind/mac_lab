import warnings
warnings.filterwarnings('ignore')

from herbie import Herbie
from herbie.toolbox import pc
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from modules import helpers, plot_setup, colormaps
import shutil
import gc
import logging
logging.getLogger("cfgrib").setLevel(logging.ERROR)
import os
os.environ["ECCODES_MESSAGES_QUIET"] = "1"
import xarray as xr
import cartopy.crs as ccrs

import s3fs

aws = s3fs.S3FileSystem(anon=True)
datestring = "20260319"
data_files, ptype_files = helpers.get_radar_files(datestring)

for i in range(360, 360, 10):
    data, precip_type = helpers.get_radar_data(data_files, ptype_files, i)

    dbz = data.where(data.values > 6.)  
    dbz["longitude"] = dbz.longitude - 360
    precip_type["longitude"] = precip_type.longitude - 360

    fig, ax = plot_setup.make_plot("Special")

    rainrate = ax.pcolormesh(dbz.longitude, 
                    dbz.latitude, 
                    dbz.values, 
                    transform = pc,
                    cmap = "snow", 
                    vmin=0,
                    vmax=60,
                    zorder=11)


    fig, cax = plot_setup.colorbar(fig, ax, rainrate, "Reflectivity (dBZ)", np.arange(0,70,10))

    plotargs = ["Polar Low ... Not a TC!", 
            "Multi-Radar Multi-Sensor (MRMS) Analysis", 
            dbz,
            "Reflectivity at Lowest Altitude (Snow Colormap)", 
            "Southern Alaska",
            "NOAA/NCEP via AWS"]
    
    plot_setup.finish_plot(fig, ax, plotargs, "group1")

    for artist in ax.collections + ax.images:
        artist.remove()

    gc.collect()

plot_setup.animate("alaska", dir="group1")
#plt.close(fig)

#shutil.rmtree("/Users/avinasharavind/data")