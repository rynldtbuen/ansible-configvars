A python script that is use as a Ansible custom filter to simplify the configuration variables defined in  [`cumulus-evpn-vxlan-ansible/master.yml`](https://github.com/rynldtbuen/cumulus-evpn-vxlan-ansible/blob/v1.0/master.yml) to deploy Cumulus EVPN VXLAN in Symmetric Routing
- **Install pip3, virtualenv and git**
```
$ sudo apt-get update
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
$ pip install cumulus_vxconfig
```
- **Clone the playbook and run a test**
```
$ git clone https://github.com/rynldtbuen/cumulus-evpn-vxlan-ansible.git && cd cumulus-evpn-vxlan-ansible
$ cumulus_getconfig -c mlag_bonds
{
    "leaf01": {
        "bonds": [
            {
                "name": "control01",
                "vids": "500-501",
                "clag_id": 1,
                "tenant": "tenant01",
                "members": "swp1",
                "alias": "tenant01.rack01.1"
            }
        ],
        "bridge": [
            {
                "mode": "vids",
                "vids": "500-501",
                "bonds": "control01"
            }
        ]
    },
...
```
