#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  download.py
#
#  Copyright 2021 Thomas Castleman <contact@draugeros.org>
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
from sys import version_info
import json
from flask import Flask, request, redirect
import urllib3

ipinfo = ["https://ipinfo.io/", "/json"]


if version_info[0] == 2:
    __eprint__("Please run with Python 3 as Python 2 is End-of-Life.")
    exit(2)
app = Flask(__name__)


@app.route("/")
def get_url():
    """get IP address of client and return optimal URL for user"""
    # get ip address
    ip_addr = request.remote_addr
    http = urllib3.PoolManager()
    data = http.request("GET", str(ip_addr).join(ipinfo)).data
    data = json.loads(data)
    # This should only be triggered during local development
    if "bogon" in data:
        if data["bogon"] is True:
            data = {"country": "US", "loc": "0,0"}
    # parsing loc back appart after setting it is a stupid thing to do, but
    # doing it this way saves us having to do an if statement, and therefore
    # fewer lines of code, and potentially not missing a branch prediction
    data["loc"] = data["loc"].split(",")
    server = get_optimal_server(data["loc"])
    return redirect(server)


def get_optimal_server(loc):
    """Get optimal server for location"""
    # Get our server list
    try:
        with open("servers.json", "r") as file:
            data = json.load(file)
    except (FileNotFoundError, PermissionError):
        http = urllib3.PoolManager()
        data = http.request("GET", "https://raw.githubusercontent.com/drauger-os-development/download-optimizer/master/servers.json").data
        data = json.loads.data
    servers = {}
    distances = []
    for continents in data:
        if data[continents] == "other":
            continue
        for side in data[continents]:
            if len(data[continents][side]) != 0:
                for server in data[continents][side]:
                    distance = calculate_distance(loc, server[1])
                    servers[distance] = server[0]
                    distances.append(distance)
    distances.sort()
    return servers[distances[0]]


def calculate_distance(p1, p2):
    """Calculate distance between 2 points"""
    if not isinstance(p1, list):
        raise TypeError("p1 is not of type 'list'")
    if not isinstance(p2, list):
        raise TypeError("p2 is not of type 'list'")
    for each in enumerate(p1):
        p1[each[0]] = float(p1[each[0]])
    for each in enumerate(p2):
        p2[each[0]] = float(p2[each[0]])
    # If they are on the same X or Y coordinate we can save time by just getting the
    # difference between the values for the coordinates on the disimilar axis
    if p1[0] == p2[0]:
        return p1[1] - p2[1]
    if p1[1] == p2[1]:
        return p1[0] - p2[0]
    # Here, we KNOW they aren't on the same X or Y coordinate. So we can make a
    # virtual, 3rd point and use the Pythagorean theorum to get the distance
    return ((p1[0] ** 2) + (p2[1] ** 2)) ** 0.5


if __name__ == "__main__":
    app.run()
