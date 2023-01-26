#!/bin/bash
# -*- coding: utf-8 -*-
#
#  update.sh
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
set -Ee
set -o pipefail
echo "Pulling updates . . ."
git pull
# Check to see if there are any updates
if [ -f .git_commit_number ]; then
	num_git=$(git log | grep "^commit " | head -n1 | awk '{print $2}')
	num_file=$(<.git_commit_number)
	if [ "$num_git" == "$num_file" ]; then
		# no updates. Exit.
		exit
	fi
fi
# We need to figure out what port was configured beforehand so that the user's settings are retained
port=$(grep "listen *.*;" /etc/nginx/sites-available/download_optimizer.conf | awk '{print $2}' | sed 's/;//g')

# uninstall download_optimizer
echo "Deconfiguring . . ."
./uninstall.sh

# reinstall download_optimizer
echo "Reconfiguring . . ."
./setup.sh "$port"

echo "Update complete!"
