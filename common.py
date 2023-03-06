#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  common.py
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
"""Common functions"""
import os

CURRENT_COUNT_FILE = "daily_count.txt"
LONG_TERM_COUNT_FILE = "download_count_longterm.txt"

def parse_data(data):
    """Parse data file text"""
    data_parsed = data.split("\n")
    for each in range(len(data_parsed) - 1, -1, -1):
        if data_parsed[each] == "":
            del data_parsed[each]
            continue
        data_parsed[each] = data_parsed[each].split(" - ")
        data_parsed[each][1] = int(data_parsed[each][1])
        data_parsed[each][0] = data_parsed[each][0].split(" ")
    return data_parsed


def parse_data_file(file):
    """Parse data file"""
    try:
        with open(file, "r") as contents:
            return parse_data(contents.read())
    except (FileNotFoundError, IOError):
        write_data_file(file)
        return []


def write_data_file(file, write=""):
    """Append data to data file"""
    if not os.path.exists(file):
        with open(file, "w") as file:
            if write == "":
                file.write("")
            else:
                for each in write:
                    file.write(f"{ ' '.join(each[0]) } - { each[1] }")
    else:
        with open(file, "a") as file:
            for each in write:
                file.write(f"\n{ ' '.join(each[0]) } - { each[1] }")
