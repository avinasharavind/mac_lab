#imports
import json
import pandas as pd  # type: ignore
import time, calendar

def get_hours(outlook, griddata):
    #get required hourly data from hours.json
    periods = []
    for ts in outlook:
        info = []
        info.append(ts["number"])

        stTime = ts["startTime"]
        stTime = time.strptime(stTime, "%Y-%m-%dT%H:%M:%S%z")
        stTime = time.strftime("%Y-%m-%dT%H:%M:%S", stTime)
        info.append(stTime)

        readTime = time.strptime(stTime, "%Y-%m-%dT%H:%M:%S")
        readTime = time.strftime("%I %p, %a %b %d", readTime)
        info.append(readTime)

        info.append(ts["temperature"])
        info.append(ts["probabilityOfPrecipitation"]["value"])

        tdc = ts["dewpoint"]["value"]
        tdf = ((tdc*9)/5)+32
        info.append(int(tdf))

        info.append(ts["relativeHumidity"]["value"])
        info.append(ts["windSpeed"][:-4])
        if ts["windDirection"] == "":
            info.append("Calm")
        else:
            info.append(ts["windDirection"])
        
        string = ts["icon"]
        string = string.split("/")
        string = string[-1]
        string = string.split("?")
        string = string[0]
        string = string.split(",")
        string = string[0]
        info.append(string)

        info.append(ts["shortForecast"])

        periods.append(info)
    
    periods = pd.DataFrame(data=periods, columns=["pdNum", "stTime", "readTime", "temp", "PoPs", "dewpt", "relHum", "wdSpd", "wdDir", "icon", "shrtFcst"])

    #get required data from griddata.json
    feelsLike = []
    for entry in griddata["properties"]["apparentTemperature"]["values"]:

        stTime = entry["validTime"]
        stTime = time.strptime(stTime[:25], "%Y-%m-%dT%H:%M:%S%z")
        stTime = calendar.timegm(stTime)
        stTime = time.localtime(stTime)
        stTime = time.strftime("%Y-%m-%dT%H:%M:%S", stTime)

        tappc = entry["value"]
        tappf = ((tappc*9)/5)+32
        tappf = str(int(round(tappf, 2)))

        hour = [stTime, tappf]
        feelsLike.append(hour)
    feelsLike = pd.DataFrame(data=feelsLike, columns = ["stTime", "appTemp"])
    periods = periods.join(feelsLike.set_index("stTime"), on="stTime")
    
    cloudCover = []
    for entry in griddata["properties"]["skyCover"]["values"]:

        stTime = entry["validTime"]
        stTime = time.strptime(stTime[:25], "%Y-%m-%dT%H:%M:%S%z")
        stTime = calendar.timegm(stTime)
        stTime = time.localtime(stTime)
        stTime = time.strftime("%Y-%m-%dT%H:%M:%S", stTime)

        hour = [stTime, str(int(round(entry["value"], 2)))]
        cloudCover.append(hour)
    cloudCover = pd.DataFrame(data=cloudCover, columns = ["stTime", "cldCvr"])
    periods = periods.join(cloudCover.set_index("stTime"), on="stTime")

    windGust = []
    for entry in griddata["properties"]["windGust"]["values"]:

        stTime = entry["validTime"]
        stTime = time.strptime(stTime[:25], "%Y-%m-%dT%H:%M:%S%z")
        stTime = calendar.timegm(stTime)
        stTime = time.localtime(stTime)
        stTime = time.strftime("%Y-%m-%dT%H:%M:%S", stTime)

        wdGstKph = entry["value"]
        wdGstMph = wdGstKph/1.609344

        hour = [stTime, str(int(round(wdGstMph, 0)))]
        windGust.append(hour)
    windGust = pd.DataFrame(data=windGust, columns = ["stTime", "wdGst"])
    periods = periods.join(windGust.set_index("stTime"), on="stTime")

    periods = periods.ffill(axis=0)
    periods = periods.bfill(axis=0)

    periods.to_csv("cache/forecasts/hourData.csv")

