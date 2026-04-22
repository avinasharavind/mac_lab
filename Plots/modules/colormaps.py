import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


'''
Temperature (°F)
Useful for:
* 2m Temperature
* 2m Dewpoint
* 2m Apparent Temperature
* Near-surface upper level temperatures/dewpoints
'''
colorlist1 = ["#E496FA", "#A346CD", "#361BBA", "#4F7AFC", "#47B7DA"]
colorlist2 = ["#009643", "#89D244", "#FCFC4E", "#FF7835", "#F83535", "#A80000", "#EF43E1"]

cmap = mpl.colors.LinearSegmentedColormap.from_list("temp_below", colorlist1, N=62)
cmap2 = mpl.colors.LinearSegmentedColormap.from_list("temp_above", colorlist2, N=48)

mpl.colormaps.register(cmap, name="temp_below", force=True)
mpl.colormaps.register(cmap2, name="temp_above", force=True)

cm1 = plt.get_cmap("temp_below")(np.linspace(0,1,62))
cm2 = plt.get_cmap("temp_above")(np.linspace(0,1,88))

colors = np.concat([cm1, cm2])
cmap = mpl.colors.LinearSegmentedColormap.from_list('temperature', colors)
mpl.colormaps.register(cmap, name="tmpf", force=True)


"""
Radar (dBZ)
Useful for:
* Model Reflctivity
* MRMS
"""
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

mpl.colormaps.register(cmap, name="radar", force=True)

"""
Snow (dBZ)
Useful for:
* Model Reflctivity
* MRMS
"""

colorlist1 = ["#36383A00", "#ABB7CC40", "#94B2E890", "#7AA7F5E6", "#2A76FAFF"] #0-25
colorlist2 = ["#225AF4FF", "#2F35E8", "#2C1ECAFF", "#0B0084"] #25-40
colorlist3 = ["#450D9FFF", "#6822AE", "#9349D3", "#692C8A"] #40-60

cmap = mpl.colors.LinearSegmentedColormap.from_list("sn1", colorlist1, N=25)
cmap2 = mpl.colors.LinearSegmentedColormap.from_list("sn2", colorlist2, N=15)
cmap3 = mpl.colors.LinearSegmentedColormap.from_list("sn3", colorlist3, N=20)

mpl.colormaps.register(cmap, name="sn1", force=True)
mpl.colormaps.register(cmap2, name="sn2", force=True)
mpl.colormaps.register(cmap3, name="sn3", force=True)

cm1 = plt.get_cmap("sn1")(np.linspace(0,1,25))
cm2 = plt.get_cmap("sn2")(np.linspace(0,1,15))
cm3= plt.get_cmap("sn3")(np.linspace(0,1,20))

colors = np.concat([cm1, cm2, cm3])
cmap = mpl.colors.LinearSegmentedColormap.from_list('snow', colors)
mpl.colormaps.register(cmap, name="snow", force=True)

cmap.set_under("#00000000")
cmap.set_bad("#00000000")

"""
Relative Vorticity (1e-5 1/s)
"""

colorlist1 = ["#553CB0DB", "#685CC4C5", "#9DA0DD6B", "#F1F1F155"]
colorlist2 = ["#FFFDC2", "#FFFA5E", "#F3CE4B", "#FDB140", "#FA8730", "#FD5050", "#FF68B4"]

cmap = mpl.colors.LinearSegmentedColormap.from_list("vort_below", colorlist1, N=40)
cmap2 = mpl.colors.LinearSegmentedColormap.from_list("vort_above", colorlist2, N=60)

mpl.colormaps.register(cmap, name="vort_below", force=True)
mpl.colormaps.register(cmap2, name="vort_above", force=True)

cm1 = plt.get_cmap("vort_below")(np.linspace(0,1,40))
cm2 = plt.get_cmap("vort_above")(np.linspace(0,1,60))

colors = np.concat([cm1, cm2])
cmap = mpl.colors.LinearSegmentedColormap.from_list('vort', colors)
mpl.colormaps.register(cmap, name="vort", force=True)
