A python script use as a Ansible custom filter in https://github.com/rynldtbuen/cumulus-vxlan-evpn-ansible.git to simplify the configuration variables defined in 'master.yml' in the  playbook.
- **Install pip3 and git package**
```
sudo apt-get install python3-pip git
pip3 install virtualenv
```
- **Create a python virtual environment**
```
mkdir venv # Create a directory for the virtual environment
virtualenv --python=python3.5 venv # Make sure python3 is use in creating the virtualenv
source venv/bin/activate # Active the virtual environment
```
- **Clone and install the script**
```
git clone https://github.com/rynldtbuen/vxlan-evpn-configvars.git
cd vxlan-evpn-configvars
pip install .
```
- **Run test**

  Change to `test` directory and run the commands below

  ```
  python configvars.py --config mlag_bonds
  # Example output
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
