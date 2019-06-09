A python script that simplify the configuration variables defined in `master.yml` and use it as a custom filter in [cumulus-vxlan-evpn-ansible](https://github.com/rynldtbuen/cumulus-vxlan-evpn-ansible.git) to load the simplified configuration variables to deploy Cumulus VXLAN EVPN
- **Install pip3, virtualenv and git**
```
$ sudo apt-get install python3-pip git
$ pip3 install virtualenv
```
- **Create and activate the virtual environment**
```
$ mkdir <DIR>
$ virtualenv -p python3 <DIR>  
$ source <DIR>/bin/activate
```
- **Install the script**
```
$ pip install cl_vx_config
```
