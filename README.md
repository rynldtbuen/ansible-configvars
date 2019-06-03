Simplify configuration variables defined in 'master.yml' to deploy Cumulus EVPN VXLAN. Use as a custom filter in Ansible to load the simplified configurations.

*** This is only intended for lab environment. Tested on fresh install Ubuntu 16.04.5 ***

##### 1. Install Prerequisites
*** Note that it is recommended to create a Python Virtual Environment and run everything from there unless you have a machine intended for this. ***
```
# Python3.5 and above is required
sudo apt-get install python3-pip git
```

```
# Create a directory and a virtual environment
mkdir vxconfigvars
pip3 install virtualenv
# Make sure python3 is use in creating the virtualenv
virtualenv --python=python3.5 vxconfigvars
source vxconfigvars/bin/activate
```

##### 1. Clone and install

```
git clone https://github.com/rynldtbuen/vxlan-evpn-configvars.git
cd vxlan-evpn-configvars
pip install -e .
```
