#!/bin/bash
# -*- coding: utf-8 -*-
#
#  uninstall.sh
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
echo "Removing files and disabling. . ."
sudo systemctl stop download_optimizer
sudo systemctl disable download_optimizer
sudo rm -fv /etc/nginx/sites-available/download_optimizer.conf /etc/nginx/sites-enabled/download_optimizer.conf /etc/systemd/system/download_optimizer.service
sudo systemctl restart nginx
