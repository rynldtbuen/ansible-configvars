A python script use as a Ansible custom filter in https://github.com/rynldtbuen/cumulus-vxlan-evpn-ansible.git to simplify the configuration variables defined in 'master.yml' in the  playbook.

- **Install python3.5 and git package**
```
sudo apt-get install python3-pip git
```

- **Install and create a python virtual environment**
```
mkdir venv
pip3 install virtualenv
# Make sure python3 is use in creating the virtualenv
virtualenv --python=python3.5 venv
source venv/bin/activate
```

- **Clone and install the script**
```
git clone https://github.com/rynldtbuen/vxlan-evpn-configvars.git
cd vxlan-evpn-configvars
pip install .
```

- **Run test**
```
cd test
python configvars.py --config mlag_bonds
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
