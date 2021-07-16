#!/bin/bash
echo "Removing files and disabling. . ."
sudo systemctl disable download_optimizer
sudo rm -fv /etc/nginx/sites-available/download_optimizer.conf /etc/nginx/sites-enabled/download_optimizer.conf /etc/systemd/system/download_optimizer.service
sudo systemctl restart nginx
