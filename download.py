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
import sys
import time
import math
from flask import Flask, request, redirect, render_template, send_from_directory, url_for
import urllib3
import archive
import random as rand
import common

MODE = False
if __name__ == "__main__":
    if ("--debug" in sys.argv) or ("-debug" in sys.argv) or ("-d" in sys.argv):
        MODE = True


def haversine(point_1, point_2, units="km"):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lat1, lon1 = point_1
    lat2, lon2 = point_2
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    if units.lower() in ("k", "km", "kilo", "kilometers", "kilometer", "metric"):
        r = 6371
    elif units.lower() in ("m", "mi", "miles", "mile", "imperial"):
        r = 3956
    return c * r


IPINFO = ["https://ipinfo.io/", "/json"]
APP = Flask(__name__)

# Multithreading stuffs
LOCK = multiprocessing.Lock()
COUNTER = multiprocessing.RawValue("i", 0)
DATA_COUNTER = multiprocessing.RawValue("L", 0)

if not os.path.exists(common.CURRENT_COUNT_FILE):
    with open(common.CURRENT_COUNT_FILE, "w") as file:
        file.write("0,0")

if not os.path.exists(common.LONG_TERM_COUNT_FILE):
    common.write_data_file(common.LONG_TERM_COUNT_FILE)


def update_download_count():
    """periodically update stored download count"""
    global COUNTER, DATA_COUNTER, LOCK
    while True:
        # We dont have to be fast about this since this process is quick as it is
        time.sleep(900)
        with LOCK:
            with open(common.CURRENT_COUNT_FILE, "r") as file:
                values = file.read().split(',')
            count = values[0]
            print("values: " + str(values))
            data_count = values[1]
            try:
                count = int(count)
                data_count = float(data_count)
            except ValueError:
                count = 0
                data_count = 0

            count = count + COUNTER.value
            data_count = data_count + DATA_COUNTER.value / 1024 # converting the data counter MB value into GB rounded to the 3rds place
            COUNTER.value = 0
            DATA_COUNTER.value = 0
            with open(common.CURRENT_COUNT_FILE, "w") as file:
                file.write(f"{count},{data_count}")
        # At this point the multitreading-sensitive stuff is done, so release the lock
        hour = time.localtime()[3]
        if hour == 0:
            # we didn't delete the `count` var. So we can reuse that.
            # also, log download counts in multiple places in case of data corruption.
            # we need to backdate the download count by a day since we commit the data to long-term storage
            # the day after it is collected
            date = time.time() - 86400
            date = time.localtime(date)
            date = time.strftime("%B %d %Y", date).split(" ")
            common.write_data_file(common.LONG_TERM_COUNT_FILE, write=[date, count, data_count])
            with open(common.CURRENT_COUNT_FILE, "w") as file:
                file.write("0,0")
            print(f"Download count for { date }: { count }, { data_count } GB")
            dedup_entries()
            archive.create_archive()


def dedup_entries():
    """Deduplicate download count entries"""
    data = common.parse_data_file(common.LONG_TERM_COUNT_FILE)
    result = []
    for each in enumerate(data):
        add = []
        for each1 in enumerate(data):
            if each[1][0] == each1[1][0]:
                if add == []:
                    sentenal = False
                    for each2 in result:
                        if each[1][0] == each2[0]:
                            sentenal = True
                            break
                    if sentenal:
                        continue
                    if each[0] == each1[0]:
                        add = [each[1][0], each[1][1]]
                    else:
                        add = [each[1][0], (each[1][1] + each1[1][1])]
                elif add[0] == each[1][0]:
                    add[1] = add[1] + each1[1][1]
                else:
                    sentenal = False
                    for each2 in result:
                        if each[1][0] == each2[0]:
                            sentenal = True
                            break
                    if sentenal:
                        continue
                    if each[0] == each1[0]:
                        add = [each[1][0], each[1][1]]
                    else:
                        add = [each[1][0], (each[1][1] + each1[1][1])]
        if add != []:
            result.append(add)
    os.remove(common.LONG_TERM_COUNT_FILE)
    for each in result:
        common.write_data_file(common.LONG_TERM_COUNT_FILE, write=each)


@APP.route("/<path:path>")
def get_url(path, mode=MODE):
    """get IP address of client and return optimal URL for user"""
    # I know this is really bad to do but it works so meh?
    global COUNTER, DATA_COUNTER, LOCK
    # todo: set DATA_COUNTER to 0 at some point before using
    # get ip address
    # I know this is non-standard but with the reverse proxy we use it works
    if mode:
        ip_addr = request.remote_addr
    else:
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
    try:
        data["loc"] = data["loc"].split(",")
    except KeyError:
        print(f"ERROR PARSING LOCATION FOR IP ADDRESS: { ip_addr }")
        print(f"Returned info from ipinfo.io:\n{ json.dumps(data, indent=2) }\n")
        print("Assuming location of 0,0...")
        data["loc"] = ["0", "0"]
    server = get_optimal_server(data["loc"])

    # Get the Content-Length header from the response, which contains the file size in bytes
    file_info = http.request("HEAD", server + path)
    file_size_bytes = file_info.headers.get('Content-Length', 0)
    file_size = str(int(file_size_bytes) // 1048576) #convert from bytes to MB

    # Only count ISO downloads, but not DEV ISOs as those are super informal
    if ((path[-4:] == ".iso") and ("DEV" not in path)):
        with LOCK:
            COUNTER.value += 1
            DATA_COUNTER.value += int(file_size)
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
    if	 loc == ["0", "0"]:
        # randomly select a server
        while True:
            area = rand.sample(sorted(data.keys()), 1)[0]
            if data[area] != []:
                break
        data = data[area]
        # go ahead and return the server. If this server is down, the user is most likely going to try again
        # if they do, they will likely get a different server
        return data[0][0]
    servers = {}
    distances = []
    for continents in data:
        if len(data[continents]) != 0:
            for server in data[continents]:
                distance = calculate_distance(loc, server[1])
                servers[distance] = server[0]
                distances.append(distance)
    distances.sort()
    return check_online(servers, distances)


def check_online(servers: dict, distances: list) -> str:
    """Return first server that is online"""
    http = urllib3.PoolManager()
    errors = (urllib3.exceptions.MaxRetryError,
              #urllib3.exceptions.NameResolutionError,
              urllib3.exceptions.NewConnectionError,
              urllib3.exceptions.ProtocolError)
    for each in distances:
        url = servers[each]
        print(f"Trying { url }")
        try:
            http.request("GET", url + "ISOs")
        except errors:
            try:
                http.request("GET", url + "hash_files")
            except errors:
                print(f"WARNING: { url } MAY BE **DOWN**")
                continue
        return url


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
    distance = haversine(point_1, point_2, units='km')
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
    data = common.parse_data_file(common.LONG_TERM_COUNT_FILE)
    # parse the data. Keep the unparsed data or display later
    try:
        with open(common.CURRENT_COUNT_FILE, "r") as file:
            current = file.read()
    except (IOError, FileNotFoundError):
        current = 0
    try:
        current = int(current) + COUNTER.value
    except ValueError:
        current = COUNTER.value
    if not isinstance(current, int):
        current = 0
    if data in ([], ""):
        return render_template("stats-none.html", daily_total=current)
    # get monthly totals
    monthly_totals = {data[0][0][0]: {"total": 0, "days": 0}}
    month_name_ptr = 0
    for each in enumerate(data):
        if data[month_name_ptr][0][0] != data[each[0]][0][0]:
            month_name_ptr = each[0]
            monthly_totals[data[month_name_ptr][0][0]] = {"total": 0, "days": 0}
        monthly_totals[data[month_name_ptr][0][0]]["total"] += data[each[0]][1]
        monthly_totals[data[month_name_ptr][0][0]]["days"] += 1
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
    if len(data) >= 7:
        for each in range(len(data) - 1, len(data) - 8, -1):
            week_avrg = week_avrg + data[each][1]
        week_avrg = "%.2f" % (week_avrg / 7)
        week_avrg = " ".join(data[-7][0][:-1]) + " thru " + " ".join(data[-1][0][:-1]) + " - " + week_avrg
    else:
        week_avrg = "0"
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
    max = 7
    if len(data) < 7:
        max = len(data)
    for each in range(max, 0, -1):
        each = each * -1
        sdt[" ".join(data[each][0])] = data[each][1]
    # Generate output for previous ALL days
    att = {}
    for each in range(len(data) - 1, 0, -1):
        each = each * -1
        att[" ".join(data[each][0])] = data[each][1]
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


@APP.route("/stats/archive/<date>")
def get_historical_stats(date):
    """Get historical statistics data"""
    if "-" in date:
        date = date.split("-")
        for each in enumerate(date):
            date[each[0]] = int(each[1])
    elif date.isnumeric():
        date = int(date)
    else:
        # not a valid entry. Return error page
        return ""
    try:
        archives = os.listdir("archives")
    except FileNotFoundError:
        # return no data available error
        return ""
    use = []
    if isinstance(date, int):
        for each in archives:
            if date in each:
                use.append(each)
    else:
        for each in date:
            for each1 in archives:
                if each in each1:
                    use.append(each1)
    # we now have our archive list in `use`
    return ""


@APP.route("/do-assets/<path:path>")
def static_dir(path):
    """Handle asset requests"""
    if ".." in path:
        return redirect(url_for("forbidden"))
    return send_from_directory("assets", path)


@APP.route("/robots.txt")
def robot_txt():
    """Provide robots.txt"""
    return static_dir("etc/robots.txt")


@APP.route("/stats/archive")
def get_valid_date_ranges():
    """Help user define valid date ranges for historical archives"""
    dates = archive.get_valid_year_range()
    valid = []
    for each in range(int(dates[0]), int(dates[1]) + 1):
        valid.append(each)
    print(valid)
    return ""


proc = multiprocessing.Process(target=update_download_count)
proc.start()

if __name__ == "__main__":
    APP.run(host="0.0.0.0", debug=MODE)
