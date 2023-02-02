#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  download.py
#
#  Copyright 2023 Thomas Castleman <contact@draugeros.org>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#
"""Redirect to the server closest to you for the fastest downloads!"""
import json
import multiprocessing
import os
import time
import haversine
import tarfile as tar
from flask import Flask, request, redirect, render_template
import urllib3

IPINFO = ["https://ipinfo.io/", "/json"]
APP = Flask(__name__)

# Set up persistant download counters
CURRENT_COUNT_FILE = "daily_count.txt"
LONG_TERM_COUNT_FILE = "download_count_longterm.txt"

# Multithreading stuffs
LOCK = multiprocessing.Lock()
COUNTER = multiprocessing.RawValue("i", 0)

if not os.path.exists(CURRENT_COUNT_FILE):
    with open(CURRENT_COUNT_FILE, "w") as file:
        file.write("0")

if not os.path.exists(LONG_TERM_COUNT_FILE):
    with open(LONG_TERM_COUNT_FILE, "w") as file:
        file.write("")


def update_download_count():
    """periodically update stored download count"""
    global COUNTER, LOCK
    sentenal = True
    while True:
        # We dont have to be fast about this since this process is quick as it is
        time.sleep(900)
        with LOCK:
            with open(CURRENT_COUNT_FILE, "r") as file:
                count = file.read()
            try:
                count = int(count)
            except ValueError:
                count = 0
            count = count + COUNTER.value
            COUNTER.value = 0
            with open(CURRENT_COUNT_FILE, "w") as file:
                file.write(str(count))
        # At this point the multitreading-sensitive stuff is done, so release the lock
        hour = time.localtime()[3]
        if ((hour == 0) and (sentenal)):
            # we didn't delete the `count` var. So we can reuse that.
            # also, log download counts in multiple places in case of data corruption.
            # we need to backdate the download count by a day since we commit the data to long-term storage
            # the day after it is collected
            date = time.time() - 86400
            date = time.localtime(date)
            date = time.strftime("%B %d %Y", date)
            with open(LONG_TERM_COUNT_FILE, "a") as file:
                file.write(f"{ date } - { count }\n")
            with open(CURRENT_COUNT_FILE, "w") as file:
                file.write("0")
            print(f"Download count for { date }: { count }")
            sentenal = False
            with open(LONG_TERM_COUNT_FILE, "r") as file:
                data = file.read().split("\n")
            # this block should only run yearly
            if len(data) >= 365:
                back_up = data[:366]
                keep = data[366:]
                del data
                keep = "\n".join(keep)
                with open(LONG_TERM_COUNT_FILE, "w") as file:
                    file.write(keep)
                del keep
                if not os.path.exists("archives"):
                    os.mkdir("archives")
                y_1 = back_up[0].split(" ")[2]
                y_2 = back_up[-1].split(" ")[2]
                years = f"{ y_1 }-{ y_2 }"
                del y_1,y_2
                with open(f"archives/{years}.txt", "w+") as file:
                    file.write("\n".join(back_up))
                with tar.open(f"archives/{ years }.tar.xz", "w:xz") as tarfile:
                    tarfile.add(f"archives/{years}.txt")
                os.remove(f"archives/{years}.txt")
        elif ((hour != 0) and (not sentenal)):
            sentenal = True


@APP.route("/<path:path>")
def get_url(path):
    """get IP address of client and return optimal URL for user"""
    # I know this is really bad to do but it works so meh?
    global COUNTER, LOCK
    # get ip address
    # I know this is non-standard but with the reverse proxy we use it works
    ip_addr = request.host
    http = urllib3.PoolManager()
    backup = {"country": "US", "loc": "0,0"}
    try:
        data = http.request("GET", str(ip_addr).join(IPINFO)).data
    except urllib3.exceptions.MaxRetryError:
        print("No internet access. In testing?")
        print("Assuming IP is bogon...")
        data = '{"bogon": true}'
    data = json.loads(data)
    # This should only be triggered during local development
    if (("bogon" in data) or ("error" in data)):
        try:
            if data["bogon"] is True:
                data = backup
        except KeyError:
            if data["error"]["title"].lower() == "wrong ip":
                data = backup
    # parsing loc back appart after setting it is a stupid thing to do, but
    # doing it this way saves us having to do an if statement, and therefore
    # fewer lines of code, and potentially not missing a branch prediction
    data["loc"] = data["loc"].split(",")
    server = get_optimal_server(data["loc"])
    # Only count ISO downloads, but not DEV ISOs as those are super informal
    if ((path[-4:] == ".iso") and ("DEV" not in path)):
        with LOCK:
            COUNTER.value += 1
    return redirect(server + path)


@APP.route("/")
def get_url_blank():
    """Handle the root directory of the mirrors"""
    return get_url("")


def get_optimal_server(loc):
    """Get optimal server for location"""
    # Get our server list
    back_up = "https://raw.githubusercontent.com/drauger-os-development/download-optimizer/master/servers.json"
    try:
        with open("servers.json", "r") as file:
            data = json.load(file)
    except (FileNotFoundError, PermissionError):
        http = urllib3.PoolManager()
        data = http.request("GET", back_up).data
        data = json.loads(data)
    servers = {}
    distances = []
    for continents in data:
        if len(data[continents]) != 0:
            for server in data[continents]:
                distance = calculate_distance(loc, server[1])
                servers[distance] = server[0]
                distances.append(distance)
    distances.sort()
    return servers[distances[0]]


def calculate_distance(point_1, point_2):
    """Calculate distance between 2 points"""
    if not isinstance(point_1, list):
        raise TypeError("point_1 is not of type 'list'")
    if not isinstance(point_2, list):
        raise TypeError("point_2 is not of type 'list'")
    for each in enumerate(point_1):
        point_1[each[0]] = float(point_1[each[0]])
    for each in enumerate(point_2):
        point_2[each[0]] = float(point_2[each[0]])

    # Calculate distance between the points
    distance = haversine.haversine(point_1, point_2, unit='km')
    return distance


@APP.route("/stats")
def get_stats():
    """Get download stats"""
    # settings
    if os.path.exists("settings.json"):
        with open("settings.json", "r") as file:
            link = json.load(file)["about_link"]
    else:
        link = "https://download-optimizer.draugeros.org/about"
    # Get data
    try:
        with open(LONG_TERM_COUNT_FILE, "r") as file:
            data = file.read()
    except (IOError, FileNotFoundError):
        data = ""
    # parse the data. Keep the unparsed data or display later
    try:
        with open(CURRENT_COUNT_FILE, "r") as file:
            current = file.read()
    except (IOError, FileNotFoundError):
        current = 0
    try:
        current = int(current) + COUNTER.value
    except ValueError:
        current = COUNTER.value
    if not isinstance(current, int):
        current = 0
    if data == "":
        return render_template("stats-none.html", daily_total=current)
    data_parsed = data.split("\n")
    for each in range(len(data_parsed) - 1, -1, -1):
        if data_parsed[each] == "":
            del data_parsed[each]
            continue
        data_parsed[each] = data_parsed[each].split(" - ")
        data_parsed[each][1] = int(data_parsed[each][1])
        data_parsed[each][0] = data_parsed[each][0].split(" ")
    # get monthly totals
    monthly_totals = {data_parsed[0][0][0]: {"total": 0, "days": 0}}
    month_name_ptr = 0
    for each in enumerate(data_parsed):
        if data_parsed[month_name_ptr][0][0] != data_parsed[each[0]][0][0]:
            month_name_ptr = each[0]
            monthly_totals[data_parsed[month_name_ptr][0][0]] = {"total": 0, "days": 0}
        monthly_totals[data_parsed[month_name_ptr][0][0]]["total"] += data_parsed[each[0]][1]
        monthly_totals[data_parsed[month_name_ptr][0][0]]["days"] += 1
    # get overall total
    overall_total = 0
    for each in monthly_totals:
        overall_total = monthly_totals[each]["total"] + overall_total
    # generate output for monthly_totals
    mt_output = {}
    for each in monthly_totals:
        mt_output[each] = monthly_totals[each]['total']
    # get weekly average
    week_avrg = 0
    for each in range(len(data_parsed) - 1, len(data_parsed) - 8, -1):
        week_avrg = week_avrg + data_parsed[each][1]
    week_avrg = "%.2f" % (week_avrg / 7)
    week_avrg = " ".join(data_parsed[-7][0][:-1]) + " thru " + " ".join(data_parsed[-1][0][:-1]) + " - " + week_avrg
    # generate output for monthly_avgrs
    ma_output = {}
    for each in monthly_totals:
        ma_output[each] = monthly_totals[each]["total"] / monthly_totals[each]["days"]
    # add today's numbers into the mix
    month = list(ma_output.keys())[-1]
    new_avg = (monthly_totals[month]["total"] + current) / monthly_totals[month]["days"] + 1
    ma_output[month] = new_avg
    # Generate output for previous 7 days
    sdt = {}
    for each in range(7, 0, -1):
        each = each * -1
        sdt[" ".join(data_parsed[each][0])] = data_parsed[each][1]
    # Generate output for previous ALL days
    att = {}
    for each in range(len(data_parsed) - 1, 0, -1):
        each = each * -1
        att[" ".join(data_parsed[each][0])] = data_parsed[each][1]
    output = render_template("stats.html",
                             overall_total=overall_total + current,
                             monthly_totals_labels=list(mt_output.keys()),
                             monthly_totals_values=list(mt_output.values()),
                             monthly_avrgs_labels=list(ma_output.keys()),
                             monthly_avrgs_values=list(ma_output.values()),
                             week_avrg=week_avrg,
                             week_total_labels=list(sdt.keys()),
                             week_total_values=list(sdt.values()),
                             daily_total_labels=list(att.keys()),
                             daily_total_values=list(att.values()),
                             daily_total=current,
                             about_link=link
                             )
    output = output.replace("&lt;", "<")
    output = output.replace("&gt;", ">")
    output = output.replace("&#34;", '"')
    output = output.replace("&#39;", "'")
    return output


@APP.route("/about")
def about():
    """Serve about page"""
    if os.path.exists("settings.json"):
        with open("settings.json", "r") as file:
            link = json.load(file)["stats_link"]
    else:
        link = "https://download-optimizer.draugeros.org/stats"
    return render_template("about.html", stats_link=link)


@APP.route("/stats/archive/<date:date>")
def get_historical_stats(date):
    """Get historical statistics data"""
    pass


proc = multiprocessing.Process(target=update_download_count)
proc.start()

if __name__ == "__main__":
    APP.run(host="0.0.0.0", debug=False)
