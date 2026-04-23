from flask import Flask, jsonify, render_template, Response, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import yaml 
import os 
import glob
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from datetime import datetime, timezone, timedelta, UTC
from io import BytesIO
import base64
import re
import urllib.parse
from radar_helpers import plot_frame, register_radar
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt
import subprocess
import sys
import time
import xarray as xr

def run_render(script, args, timeout=120):
    """Run a render subprocess, kill it if it hangs."""
    try:
        proc = subprocess.Popen(
            [sys.executable, script] + args,
        )
        proc.wait(timeout=timeout)
        if proc.returncode != 0:
            print(f"[render] {script} exited with code {proc.returncode}")
    except subprocess.TimeoutExpired:
        print(f"[render] {script} timed out, killing")
        proc.kill()
        proc.wait()  # ensure it's fully cleaned up after kill
    except Exception as e:
        print(f"[render] {script} failed: {e}")

import warnings
warnings.filterwarnings("ignore")

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

register_radar()


'''
Gets data from various NWS sources to display.
Generated almost entirely by Claude.
'''

app = Flask(__name__)

# Load config file
with open("config.yaml") as f:
    config = yaml.safe_load(f)

# Hold cached data
CACHE_DIR = "cache"
cache = {
    "observations": None,
    "forecast_short": None,
    "surface_analysis_url": "https://www.wpc.ncep.noaa.gov/NationalForecastChart/staticmaps/noaad1.png",
    "radar_frames": [], 
    "satellite_vis_frames": [],
    "satellite_ir_frames": [],
}

spc_urls = {
    "categorical": "https://www.spc.noaa.gov/products/outlook/day1otlk.png",
    "tornado":     "https://www.spc.noaa.gov/products/outlook/day1probotlk_torn.png",
    "hail":        "https://www.spc.noaa.gov/products/outlook/day1probotlk_hail.png",
    "wind":        "https://www.spc.noaa.gov/products/outlook/day1probotlk_wind.png",
    "day2":        "https://www.spc.noaa.gov/products/outlook/day2otlk.png",
    "day3":        "https://www.spc.noaa.gov/products/outlook/day3otlk.png",
    "day4":        "https://www.spc.noaa.gov/products/exper/day4-8/day4prob.gif",
    "day5":        "https://www.spc.noaa.gov/products/exper/day4-8/day5prob.gif",
}

noaa_urls = {
    "rainfall":         "https://www.wpc.ncep.noaa.gov/qpf/94ewbg.gif",
    "24h_qpf":              "https://www.wpc.ncep.noaa.gov/qpf/fill_94qwbg.gif",
    "hazards_3_7":      "https://www.wpc.ncep.noaa.gov/threats/final/hazards_d3_7_contours.png",
    "nws_homepage":     "https://www.weather.gov/wwamap/png/US.png",
    "drought":          "https://droughtmonitor.unl.edu/data/png/current/current_usdm.png",
}

# Get observations from ASOS station
def fetch_observations():
    station = config["asos"]["station_id"]
    url = f"https://api.weather.gov/stations/{station}/observations/latest"
    headers = {"maclab-test": "maclab-display-app"}  # NWS requires this
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        props = data["properties"]

        # Pull out just the fields we care about displaying
        cache["observations"] = {
            "station":          station,
            "timestamp":        props.get("timestamp"),
            "temp_c":           props.get("temperature", {}).get("value"),
            "dewpoint_c":       props.get("dewpoint", {}).get("value"),
            "humidity_pct":     props.get("relativeHumidity", {}).get("value"),
            "wind_dir":         props.get("windDirection", {}).get("value"),
            "wind_spd_kmh":      props.get("windSpeed", {}).get("value"),
            "wind_gust_kmh":     props.get("windGust", {}).get("value"),
            "visibility_m":     props.get("visibility", {}).get("value"),
            "pressure_sl_pa":   props.get("barometricPressure", {}).get("value"),
            "sky_condition":    props.get("textDescription"),
            "weather_condition":props.get("presentWeather"),
            "raw_metar":        props.get("rawMessage"),
        }
        print(f"[obs] Updated observations for {station}")
    except Exception as e:
        print(f"[obs] Failed to fetch observations: {e}")

# Get NWS Forecast data
def fetch_forecast():
    office = config["location"]["nws_office"]
    gx     = config["location"]["nws_gridX"]
    gy     = config["location"]["nws_gridY"]
    headers = {"maclab-test": "maclab-display-app"}

    try:
        # Hourly forecast (used for the 12-hr strip)
        r = requests.get(
            f"https://api.weather.gov/gridpoints/{office}/{gx},{gy}/forecast/hourly",
            headers=headers, timeout=10
        )
        r.raise_for_status()
        hourly_periods = r.json()["properties"]["periods"][:12]  # next 12 hours

        # Daily forecast (used for the 5-day panel)
        r2 = requests.get(
            f"https://api.weather.gov/gridpoints/{office}/{gx},{gy}/forecast",
            headers=headers, timeout=10
        )
        r2.raise_for_status()
        daily_periods = r2.json()["properties"]["periods"][:10]  # ~5 days (day+night each)

        cache["forecast_short"] = {
            "hourly": hourly_periods,
            "daily":  daily_periods,
        }
        print(f"[forecast] Updated forecast for {office} {gx},{gy}")
    except Exception as e:
        print(f"[forecast] Failed to fetch forecast: {e}")

s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))

# Get Radar Data
def fetch_radar_frames(n_frames=10):
    """
    Fetch the most recent N MRMS reflectivity composite frames from AWS.
    Frames are stored as base64 strings so they can be sent as JSON to the browser.
    """
    bucket = "noaa-mrms-pds"
    date = datetime.now(UTC).strftime("%Y%m%d")
    prefix = f"CONUS/ReflectivityAtLowestAltitude_00.50/{date}"
    radar_dir = os.path.join(CACHE_DIR, "radar")
    os.makedirs(radar_dir, exist_ok=True)

    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = sorted(
            response.get("Contents", []),
            key=lambda x: x["LastModified"],
        )

        # Take the N most recent files
        if len(objects)<=5*n_frames:
            i = len(objects)
        else:
            i = 5*n_frames
        recent = objects[-i:]

        for obj in recent:
            if obj["LastModified"].minute%10 == 0:
                # Use just the filename as the local name
                fname = obj["Key"].split("/")[-1]
                dest_path = os.path.join(radar_dir, fname)
                
                if not os.path.exists(dest_path):
                    data = s3.get_object(Bucket=bucket, Key=obj["Key"])
                    with open(dest_path, "wb") as f:
                        f.write(data["Body"].read())
                    print(f"[radar] Downloaded: {fname}")

        # Trim oldest files beyond N
        all_files = sorted(glob.glob(os.path.join(radar_dir, "*.gz")))
        while len(all_files) > n_frames:
            os.remove(all_files.pop(0))

    except Exception as e:
        print(f"[radar] Failed: {e}")
    

    png_dir = os.path.join(CACHE_DIR, "radar_frames")
    os.makedirs(png_dir, exist_ok=True)

    for gz_path in sorted(glob.glob(os.path.join(radar_dir, "*.gz"))):
        fname = os.path.basename(gz_path)
        png_path = os.path.join(png_dir, fname.replace(".gz", ".png"))

        if not os.path.exists(png_path):
            try:
                generate_radar_frames(gz_path, png_path)
                print(f"[radar] Rendered: {png_path}")
            except subprocess.TimeoutExpired:
                    print(f"[radar] Render timed out: {fname}")
            except subprocess.CalledProcessError as e:
                    print(f"[radar] Render failed: {fname}: {e}")

    # Trim oldest PNGs beyond N
    all_pngs = sorted(glob.glob(os.path.join(png_dir, "*.png")))
    while len(all_pngs) > n_frames:
        os.remove(all_pngs.pop(0))

    # Update cache with sorted PNG paths
    cache["radar_frames"] = sorted(glob.glob(os.path.join(png_dir, "*.png")))
    print(f"[radar] Loop has {len(cache['radar_frames'])} frames")

def generate_radar_frames(radar_frame, png_path):
    run_render("radar_helpers.py", [radar_frame, png_path])

# Get GOES Satellite Data
def fetch_goes_frames(n_frames=15):
    """
    Fetch recent GOES-16 CONUS ABI imagery from AWS.
    We use the pre-rendered GeoColor (Band 13 proxy) imagery from a NOAA image server
    rather than raw NetCDF, since rendering NetCDF requires significant processing.
    """
    # NOAA serves pre-rendered GOES imagery via a public image server —
    # much easier than processing raw L2 NetCDF files from S3.
    base_url = "https://cdn.star.nesdis.noaa.gov/GOES19/ABI"
    products = {
        "CONUS-GEOCOLOR-5000x3000": ("CONUS/GEOCOLOR", "satellite_vis_frames"),
        "CONUS-13-5000x3000":  ("CONUS/13",       "satellite_ir_frames"),
        "ne-GEOCOLOR-1200x1200": ("SECTOR/NE/GEOCOLOR", "ne_vis_frames"),
        "ne-13-1200x1200": ("SECTOR/NE/13", "ne_ir_frames"),
        "ne-DayNightCloudMicroCombo-1200x1200": ("SECTOR/NE/DayNightCloudMicroCombo", "ne_cloud_frames"),
        "ne-09-1200x1200": ("SECTOR/NE/09", "ne_band9_frames"),
    }

    for label, (product, cache_key) in products.items():
        try:
            listing_url = f"{base_url}/{product}/"
            r = requests.get(listing_url, timeout=10)
            r.raise_for_status()

            matches = re.findall(
                rf'href="(\d+_GOES19-ABI-{label}\.jpg)"',
                r.text
            )
            if not matches:
                print(f"[goes-{label}] No frames found in listing")
                continue

            product_dir = os.path.join(CACHE_DIR, f"goes_{label}")
            os.makedirs(product_dir, exist_ok=True)

            # Download any missing frames from the last N in the listing
            recent_fnames = sorted(matches)[-n_frames:]
            for fname in recent_fnames:
                dest_path = os.path.join(product_dir, fname)
                if not os.path.exists(dest_path):
                    img_url = f"{base_url}/{product}/{fname}"
                    img_r = requests.get(img_url, timeout=10)
                    img_r.raise_for_status()
                    with open(dest_path, "wb") as f:
                        f.write(img_r.content)
                    print(f"[goes-{label}] Saved new frame: {fname}")

            # Trim any frames older than the current N we want
            all_frames = sorted(glob.glob(os.path.join(product_dir, "*.jpg")))
            while len(all_frames) > n_frames:
                os.remove(all_frames.pop(0))

            # Load frames from disk into cache as base64
            cache[cache_key] = []
            for fpath in sorted(glob.glob(os.path.join(product_dir, "*.jpg"))):
                with open(fpath, "rb") as f:
                    cache[cache_key].append(
                        base64.b64encode(f.read()).decode("utf-8")
                    )

            print(f"[goes-{label}] Loop has {len(cache[cache_key])} frames")

        except Exception as e:
            print(f"[goes-{label}] Failed: {e}")

def model_frames_are_stale(model_dir, max_age_hours=3):
    existing = glob.glob(os.path.join(model_dir, "*.png"))
    if not existing:
        return True
    if len(existing)<12:
        return True
    newest = max(os.path.getmtime(f) for f in existing)
    age_hours = (time.time() - newest) / 3600
    return age_hours > max_age_hours

def generate_hrrr_surface():
    model_dir = os.path.join(CACHE_DIR, "hrrr_surface")
    os.makedirs(model_dir, exist_ok=True)

    try:
        print("[hrrr-surface] Entering HRRR plotting scheme")
        for i in range(12):
            if not model_frames_are_stale(model_dir):
                print("[hrrr-surface] Frames are current, skipping render")
                return
            elif os.path.exists(f"frame{i+10}.png"):
                print(f"[hrrr-surface] Frame {i} already exists, skipping")
                continue
            else:
                print(f"[hrrr-surface] Proceeding into frame {i}")
                run_render("hrrr_model.py", [f"{i}"])
    except:
        print("[hrrr-surface] Something went wrong.")


# Flask routes
@app.route("/")
def index():
    """Serve the main dashboard page."""
    return render_template("index.html")

@app.route("/api/observations")
def observations():
    """Return latest cached ASOS observations as JSON."""
    return jsonify(cache["observations"])

@app.route("/api/forecast")
def forecast():
    """Return cached NWS forecast as JSON."""
    return jsonify(cache["forecast_short"])

@app.route("/api/surface_analysis")
def surface_analysis():
    try:
        r = requests.get(cache["surface_analysis_url"], timeout=10)
        r.raise_for_status()
        print("[wpc] Retrieved surface analysis")
        return Response(r.content, mimetype="image/gif")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/noaa/<product>")
def noaa(product):
    if product not in noaa_urls:
        return jsonify({"error": "unknown product"}), 404
    try:
        r = requests.get(noaa_urls[product], timeout=10)
        r.raise_for_status()
        return Response(r.content, mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/spc/<product>")
def spc(product):
    if product not in spc_urls:
        return jsonify({"error": "unknown product"}), 404
    try:
        r = requests.get(spc_urls[product], timeout=10)
        r.raise_for_status()
        return Response(r.content, mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/satellite_vis")
def satellite_vis():
    return jsonify({"frames": cache["satellite_vis_frames"]})

@app.route("/api/satellite_ir")
def satellite_ir():
    return jsonify({"frames": cache["satellite_ir_frames"]})

@app.route("/api/ne-sat/vis")
def satellite_ne_vis():
    return jsonify({"frames": cache["ne_vis_frames"]})

@app.route("/api/ne-sat/ir")
def satellite_ne_ir():
    return jsonify({"frames": cache["ne_ir_frames"]})

@app.route("/api/ne-sat/cloud")
def satellite_ne_cloud():
    return jsonify({"frames": cache["ne_cloud_frames"]})

@app.route("/api/ne-sat/band9")
def satellite_ne_band9():
    return jsonify({"frames": cache["ne_band9_frames"]})

@app.route("/api/radar")
def radar():
    frames = []
    for fpath in cache["radar_frames"]:
        with open(fpath, "rb") as f:
            frames.append(base64.b64encode(f.read()).decode("utf-8"))
    return jsonify({"frames": frames})

@app.route("/api/hrrr_surface")
def model():
    frames = sorted(glob.glob(os.path.join(CACHE_DIR, "hrrr_surface", "*.png")))
    urls = [f"/api/hrrr_surface/frame/{os.path.basename(f)}" for f in frames]
    return jsonify({"urls": urls})

@app.route("/api/hrrr_surface/frame/<path:filename>")
def model_frame(filename):
    path = os.path.join(CACHE_DIR, "hrrr_surface", filename)
    return send_file(path, mimetype="image/png")


# Schedule cache updates.
scheduler = BackgroundScheduler()
scheduler.add_job(
    fetch_observations,
    "interval",
    seconds=config["refresh_intervals_seconds"]["observations"]
)
scheduler.add_job(
    fetch_forecast,
    "interval",
    seconds=config["refresh_intervals_seconds"]["forecast"]
)
scheduler.add_job(fetch_goes_frames, "interval",
    seconds=config["refresh_intervals_seconds"]["satellite"])

scheduler.add_job(fetch_radar_frames, "interval",
    seconds=config["refresh_intervals_seconds"]["radar"])

scheduler.add_job(generate_hrrr_surface, "interval",
    seconds=config["refresh_intervals_seconds"]["model"])

scheduler.start()

# Run fetches once immediately on startup so cache isn't empty
fetch_observations()
fetch_forecast()
fetch_goes_frames()
fetch_radar_frames()
generate_hrrr_surface()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)