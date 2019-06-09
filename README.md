A python script that is use as a Ansible custom filter to simplify the configuration variables defined in  [`cumulus-evpn-vxlan-ansible/master.yml`](https://github.com/rynldtbuen/cumulus-vxlan-evpn-ansible/blob/v2.0/master.yml) to deploy Cumulus EVPN VXLAN in Symmetric Routing
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
