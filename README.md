# Download Optimizer
Use the IP address of a client to determine the best link for them to download from, based on their location.


## Installation
On a Linux or BSD (untested) system:

```
git clone https://github.com/drauger-os-development/download-optimizer
cd download-optimizer
./setup.sh
```
After installation, you will need to open port 80 on your firewall in order to use Download Optimizer. The easiest way to do that is with UFW:

```
sudo ufw enable
sudo ufw allow 80
```

## Removal
```
./uninstall.sh
```

Remember to close port 80 if you aren't going to use it for anything else.