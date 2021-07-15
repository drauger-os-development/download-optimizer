#!/bin/bash
echo "Installing Dependencies . . ."
sudo apt install --assume-yes $(<requirements.txt)
username=$(whoami)
loc="$PWD"
echo "Configuring your system . . ."
sudo cp -v flask-app.nginx_conf /etc/nginx/sites-available/flask-app.conf
sudo ln -v /etc/nginx/sites-available/flask-app.conf /etc/nginx/sites-enabled/flask-app.conf
sudo cp -v download_optimizer.service /etc/systemd/system/download_optimizer.service
sudo sed -i "s/<path to>/$loc/g" /etc/nginx/sites-available/flask-app.conf
sudo sed -i "s/<path to>/$loc/g" /etc/systemd/system/download_optimizer.service
sudo sed -i "s/<username>/$username/g" /etc/systemd/system/download_optimizer.service
sudo systemctl enable download_optimizer
echo "Please open port 80 so that Download Optimizer may be exposed to the network"
