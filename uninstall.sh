#!/bin/bash
echo "Removing files . . ."
sudo rm -fv /etc/nginx/sites-available/flask-app.conf /etc/nginx/sites-enabled/flask-app.conf /etc/systemd/system/download_optimizer.service
