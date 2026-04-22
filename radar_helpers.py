import matplotlib as mpl
import sys
mpl.use("agg")
import matplotlib.pyplot as plt
import gc
import shutil
import gzip
import xarray as xr
from herbie.toolbox import EasyMap, pc
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

import warnings
warnings.filterwarnings("ignore")

def read_radar(data_file):
    try:
        out_path = data_file.replace(".gz", "")
        with gzip.open(data_file, "rb") as f_in:
            with open(out_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        data = xr.load_dataarray(out_path, engine="cfgrib", decode_timedelta=True)
    except Exception as e:
        print("Failed.")
    
    return data

def make_plot():

    lat1, lon1, lat2, lon2 = (41,   -79,  44,  -74)

    width_in = 6 * (lon2 - lon1) / (lat2 - lat1)
    height_in = 6
    dpi = 150
    
    # Round pixel dimensions to nearest even number
    width_px = round(width_in * dpi / 2) * 2
    height_px = round(height_in * dpi / 2) * 2

    fig = plt.figure(figsize=[width_px/dpi,height_px/dpi], constrained_layout=True, dpi=dpi)
    ax = fig.add_subplot(projection=pc)

    ax = EasyMap("10m", add_coastlines=True,
                 coastlines_kw={"color":"#1b2433"}, ax=ax)
    ax = ax.LAND(facecolor="#818A93", edgecolor="k", linewidth=1)
    ax = ax.BORDERS(color="#1b2433", linewidth=1, zorder=16)
    ax = ax.STATES(edgecolor="#1b2433", linewidth=1, zorder=15)
    ax = ax.COUNTIES(edgecolor="#1b2433", linewidth=1, zorder=15)
    ax = ax.LAKES(facecolor="#3E5C8F", linewidth=0.5, zorder=14)
    ax = ax.OCEAN(facecolor="#3E5C8F", linewidth=0.5, zorder=14)
    ax = ax.ax

    ax.set_extent([lon1, lon2, lat1, lat2], crs=pc)

    return fig, ax

def register_radar():
    colorlist1 = ["#383D4C00", "#9AA8D57C", "#5F79CFBF"] # 0-15
    cmap1 = mpl.colors.LinearSegmentedColormap.from_list("radar1",colorlist1, N=15)
    mpl.colormaps.register(cmap1, name="r1", force=True)
    cm1 = plt.get_cmap("r1")(np.linspace(0,1,15))

    colorlist2 = ["#7FD488", "#42BA32", "#37AB28", "#006D0B"] # 15-30
    cmap2 = mpl.colors.LinearSegmentedColormap.from_list("radar2",colorlist2, N=15)
    mpl.colormaps.register(cmap2, name="r2", force=True)
    cm2 = plt.get_cmap("r2")(np.linspace(0,1,15))

    colorlist3 = ["#FCF45E", "#AAAA00"] #30-40
    cmap3 = mpl.colors.LinearSegmentedColormap.from_list("radar3",colorlist3, N=10)
    mpl.colormaps.register(cmap3, name="r3", force=True)
    cm3 = plt.get_cmap("r3")(np.linspace(0,1,10))

    colorlistO = ["#FA933E", "#F95F00",] #40-50
    cmapO = mpl.colors.LinearSegmentedColormap.from_list("radarO",colorlistO, N=10)
    mpl.colormaps.register(cmapO, name="rO", force=True)
    cmO = plt.get_cmap("rO")(np.linspace(0,1,10))

    colorlist4 = ["#FF0000", "#960909"] #50-60
    cmap4 = mpl.colors.LinearSegmentedColormap.from_list("radar4",colorlist4, N=10)
    mpl.colormaps.register(cmap4, name="r4", force=True)
    cm4 = plt.get_cmap("r4")(np.linspace(0,1,10))

    colorlist5 = ["#F340BA", "#E088FD"] #60-70
    cmap5 = mpl.colors.LinearSegmentedColormap.from_list("radar5",colorlist5, N=10)
    mpl.colormaps.register(cmap5, name="r5", force=True)
    cm5 = plt.get_cmap("r5")(np.linspace(0,1,10))

    colors = np.concat([cm1, cm2, cm3, cmO, cm4, cm5])
    cmap = mpl.colors.LinearSegmentedColormap.from_list('radar', colors)
    cmap.set_under("#00000000")
    cmap.set_over("#A31AFF")
    cmap.set_bad("#00000000")

    mpl.colormaps.register(cmap, name="radar")

def plot_frame(radar_frame, png_path):
    data = read_radar(radar_frame)
    fig, ax = make_plot()
    p = ax.pcolormesh(data.longitude, data.latitude, data.values, cmap="radar", vmin=0, vmax=70, zorder=20)
    fig.canvas.draw()
    cax = inset_axes(ax, width="100%", height="5%",
                 loc="lower center",
                 bbox_to_anchor=(0, -0.08, 1, 1),
                 bbox_transform=ax.transAxes,
                 borderpad=0)

    cb = plt.colorbar(
    p,
    cax=cax,
    orientation="horizontal",
    spacing="proportional",
    ticks = np.arange(0, 75, 5), 
    )

    cb.ax.tick_params(color="#2a2724")
    cb.ax.set_xlabel("Reflectivity (dBZ)", color="#2a2724", size=21)

    fig.patch.set_facecolor("#f2f0eb")

    ax.set_title(f"{data.time.values.astype(str)[0:10]} {data.time.values.astype(str)[11:16]}Z / Upstate NY", size=21)

    plt.savefig(f"{png_path}", dpi=150, bbox_inches="tight")
    plt.close("all")
    data.close()
    del data, fig, radar_frame
    ax.cla()

if __name__ == "__main__":
    grib_path = sys.argv[1]
    png_path  = sys.argv[2]
    try:
        register_radar()
        plot_frame(grib_path, png_path)
    finally:
        plt.close("all")
        gc.collect()
        sys.exit(0)  # explicit exit to ensure full cleanup


