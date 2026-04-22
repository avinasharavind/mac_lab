llat, llon, ulat, ulon = helpers.map_sectors["Eastern US"]

ds = ds.sel(latitude=slice(ulat, llat), longitude=slice(360+llon, 360+ulon))

ug, vg = helpers.calc_geostrophic_wind(ds.gh)
relvort = helpers.d_dx(vg) - helpers.d_dy(ug)
relvort = helpers.smooth_var(relvort, 2)
relvort *= 1e5

p = ax.pcolormesh(ds.longitude, ds.latitude, relvort.values, cmap="vort", vmin=-40, vmax=60, zorder=12)
c = ax.contour(ds.longitude, ds.latitude, ds.gh, zorder=13, colors="k", linewidth=2, levels=np.arange(4600, 6060, 60))
q = ax.barbs(dsw.longitude[::15], dsw.latitude[::15], dsw.u[::15, ::15], dsw.v[::15, ::15], color="k", length=5, zorder=15, linewidth=0.5)