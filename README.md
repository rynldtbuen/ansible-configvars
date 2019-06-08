A python script that is use as a Ansible custom filter in [cumulus-vxlan-evpn-ansible](https://github.com/rynldtbuen/cumulus-vxlan-evpn-ansible.git) to simplify the configuration variables defined in 'master.yml' in the  playbook.
- **Install pip3 and git package**
```
$ sudo apt-get install python3-pip git
```
- **Install virtualenv**
```
$ pip3 install virtualenv
```
- **Create and activate the virtual environment**
```
$ mkdir <DIR>
$ virtualenv -p python3 <DIR>  
$ source <DIR>/bin/activate
```
- **Clone and install the script**
```
$ git clone https://github.com/rynldtbuen/vxlan-evpn-configvars.git
$ cd vxlan-evpn-configvars
$ pip install .
```
- **Run test**

  Change to `test` directory and run the commands below
  ```
  $ python configvars.py --config mlag_bonds
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
