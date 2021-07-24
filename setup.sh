#!/bin/bash
port="$1"
if [ "$port" == "" ]; then
	port="80"
fi
echo "Installing Dependencies . . ."
sudo apt install --assume-yes $(<requirements_apt.txt)
pip3 install -r requirements.txt
username=$(whoami)
echo "Configuring your system . . ."
sudo cp -v download_optimizer.nginx_conf /etc/nginx/sites-available/download_optimizer.conf
sudo cp -v download_optimizer.service /etc/systemd/system/download_optimizer.service
sudo sed -i "s:<path to>:$PWD:g" /etc/nginx/sites-available/download_optimizer.conf
sudo sed -i "s:<port>:$port:g" /etc/nginx/sites-available/download_optimizer.conf
sudo sed -i "s:<path to>:$PWD:g" /etc/systemd/system/download_optimizer.service
sudo sed -i "s:<username>:$username:g" /etc/systemd/system/download_optimizer.service
echo "Disabling default site . . ."
sudo rm -fv /etc/nginx/sites-enabled/default
echo "Enabling site and restarting Nginx . . ."
sudo systemctl enable download_optimizer
sudo ln -sv /etc/nginx/sites-available/download_optimizer.conf /etc/nginx/sites-enabled/download_optimizer.conf
sudo systemctl restart nginx
echo "Please open port 80 so that Download Optimizer may be exposed to the network"
