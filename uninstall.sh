#!/bin/bash
echo "Removing files and disabling. . ."
sudo systemctl disable download_optimizer
sudo rm -fv /etc/nginx/sites-available/flask-app.conf /etc/nginx/sites-enabled/flask-app.conf /etc/systemd/system/download_optimizer.service
sudo systemctl restart nginx
