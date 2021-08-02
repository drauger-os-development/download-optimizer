#!/bin/bash
# -*- coding: utf-8 -*-
#
#  setup.sh
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
port="$1"
if [ "$port" == "" ]; then
	port="80"
fi
echo "Installing Dependencies . . ."
sudo apt install --assume-yes $(<requirements_apt.txt)
# Install if not yet installed, update otherwise
pip3 install --upgrade -r requirements.txt
username=$(whoami)
echo "Configuring your system . . ."
sudo cp -v download_optimizer.nginx_conf /etc/nginx/sites-available/download_optimizer.conf
sudo cp -v download_optimizer.service /etc/systemd/system/download_optimizer.service
sudo sed -i "s:<path to>:$PWD:g" /etc/nginx/sites-available/download_optimizer.conf
sudo sed -i "s:<port>:$port:g" /etc/nginx/sites-available/download_optimizer.conf
sudo sed -i "s:<path to>:$PWD:g" /etc/systemd/system/download_optimizer.service
sudo sed -i "s:<username>:$username:g" /etc/systemd/system/download_optimizer.service

# Only bother trying to delete this file if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
	echo "Disabling default site . . ."
	sudo rm -fv /etc/nginx/sites-enabled/default
fi

echo "Enabling site and restarting Nginx . . ."
sudo systemctl enable download_optimizer
sudo ln -sv /etc/nginx/sites-available/download_optimizer.conf /etc/nginx/sites-enabled/download_optimizer.conf
sudo systemctl restart nginx
sudo systemctl start download_optimizer
echo "Please ensure port $port is open so that Download Optimizer may be exposed to the network"
