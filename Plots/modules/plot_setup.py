import matplotlib.pyplot as plt
import matplotlib.transforms as mts
from herbie import Herbie
from herbie.toolbox import EasyMap, pc
from modules import helpers, colormaps
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from os import listdir
import moviepy.video.io.ImageSequenceClip as ImageSequenceClip
import numpy as np
import cartopy.crs as ccrs



plt.style.use("mplstyles/textstyle.mplstyle")

def make_plot(location="CONUS"):
    """
    Creates a base plot for geospatial mapping using Herbie's EasyMap.

    Parameters
    ----
    location : string, default: "CONUS"
        Region to create plot for. See helpers.py for full list.

    Returns
    ----
    fig : figure
        The matplotlib figure.
    ax:  geoaxes
        The matplotlib/cartopy geoaxes.
    gs: gridspec
        The matplotlib gridspec (needed for colorbar)
    """
    lat1, lon1, lat2, lon2 = helpers.map_sectors[location]

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
    ax = ax.LAND(facecolor="#5C636A", edgecolor="k", linewidth=1)
    ax = ax.BORDERS(color="#1b2433", linewidth=1, zorder=16)
    ax = ax.STATES(edgecolor="#1b2433", linewidth=1, zorder=15)
    ax = ax.COUNTIES(edgecolor="#1b2433", linewidth=0.5, zorder=15)
    ax = ax.LAKES(facecolor="#203251", linewidth=0.5, zorder=11)
    ax = ax.OCEAN(facecolor="#1b2433", linewidth=0.5, zorder=11)
    ax = ax.ax

    ax.set_extent([lon1, lon2, lat1, lat2], crs=pc)

    ax.set_frame_on(False)

    return fig, ax

def colorbar(fig, ax, p, cbar_label, cmap_bounds):
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
    ticks = cmap_bounds, 
    )

    cb.ax.tick_params(color="#e1e8f2")
    cb.ax.set_xlabel(cbar_label, color="#e1e8f2", size=18)
    cb.outline.set_visible(False)

    return fig, cax

def rainsnow(fig, ax, pr, ps):
    fig.canvas.draw()

    cax = inset_axes(ax, width="47.5%", height="5%",
                 loc="lower left",
                 bbox_to_anchor=(0, -0.08, 1, 1),
                 bbox_transform=ax.transAxes,
                 borderpad=0)

    cb = plt.colorbar(
    pr,
    cax=cax,
    orientation="horizontal",
    spacing="proportional",
    ticks = np.arange(0,80,10), 
    )

    cb.ax.tick_params(color="#e1e8f2")
    cb.ax.set_xlabel("Rain (dBZ)", color="#e1e8f2", size=18)
    cb.outline.set_visible(False)

    cax2 = inset_axes(ax, width="47.5%", height="5%",
                 loc="lower right",
                 bbox_to_anchor=(0, -0.08, 1, 1),
                 bbox_transform=ax.transAxes,
                 borderpad=0)

    cb2 = plt.colorbar(
    ps,
    cax=cax2,
    orientation="horizontal",
    spacing="proportional",
    ticks = np.arange(0,70,10), 
    )

    cb2.ax.tick_params(color="#e1e8f2")
    cb2.ax.set_xlabel("Snow (dBZ)", color="#e1e8f2", size=18)
    cb2.outline.set_visible(False)

    return fig, cax

def clabels(ax, c):
    labels = ax.clabel(c, c.levels, inline=True, colors="k", fontsize=8, zorder=13, manual=False, rightside_up=True)

    for label in labels:
        label.set_clip_path(ax.patch)
        label.set_clip_on(True)
        label.set_bbox(dict(boxstyle="round,pad=0.3", facecolor="#9D9D9D", 
                            edgecolor="none", alpha=0.75))
    return ax

def finish_plot(fig, ax, plotargs, to):
    """
    Finishes and saves plot

    Parameters
    ----
    fig : figure
        The figure for the plot, created by make_plot.

    ax : geoaxes
        The axes for the plot, created by make_plot.

    plotargs : list
        A list of the following plot arguments to include... \\
        suptitle : string, The plot title. \\
        model : string, the model name/descriptor. \\
        ds : the data array (to parse time from). \\
        vars : string, the variables plotted. \\
        location: string, the location plotted. \
        
    to : string
        The path to save figure.

    Returns
    ----
    fig : figure
        The completed figure.

    ax : geoaxes
        The completed geoaxes.
    """
    suptitle, model, ds, vars, location, source = plotargs

    validtime = ds.time.dt.strftime('%H:%MZ %d %b %Y').item()
    inittime = ds.time.dt.strftime('%H:%MZ %d %b %Y').item()

    pos = ax.get_position()

    fig.text(pos.x0, 
        pos.y1 + 0.08,
        f"{suptitle}",
        color="#e1e8f2",
        size=30,
        ha="left", va="bottom"
        ) 
    
    fig.text(pos.x0, 
        pos.y1 + 0.01,
        f"{model} // Valid {validtime}\n{vars}  // {location}", 
        ha="left", 
        va="bottom",
        color="#aab9d1", 
        size=12)
    
    fig.text(pos.x1,
             pos.y0 - 0.22,
             "Created by Avinash Aravind",
             ha="right", 
             va="bottom",
             color="#aab9d1", 
             size=12)
    
    fig.text(pos.x0,
             pos.y0 - 0.22,
             f"Data from {source}",
             ha="left", 
             va="bottom",
             color="#aab9d1", 
             size=12)
    
    print(f"Done with {validtime}! Saving...")
    plt.savefig(f"{to}/{ds.time.dt.strftime('%d_%b_%Y_%H_%MZ').item()}.png", 
            bbox_inches=mts.Bbox([[-0.24, -1.6], [9.24, 7.]]), dpi=150)
    
    return

def animate(savename, dir="images", dur=2):
    frames = listdir(dir)
    frames.sort()
    frames = frames + [frames[-1], frames[-1]]

    # List of image file paths
    # Output GIF path
    output_path = f"loops/{savename}.mp4"
    # Create GIF
    clip = ImageSequenceClip.ImageSequenceClip([f"{dir}/{frame}" for frame in frames], durations=[dur/24]*len(frames))
    clip.write_videofile(output_path, codec='libx264', ffmpeg_params=["-pix_fmt", "yuv420p"])

    print(f"MP4 created and saved at {output_path}")