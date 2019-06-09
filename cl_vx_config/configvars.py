import collections
import copy
import itertools

from cl_vx_config.utils.checkvars import CheckVars
from cl_vx_config.utils.filters import Filters
from cl_vx_config.utils import (
    File, Inventory, Host, MACAddr, Network, Link
)

filter = Filters()
inventory = Inventory()
mf = File().master()


class ConfigVars:
    '''
    Simplify the configuration variables defined in master.yml and use as a
    custom filter in Ansible to load the simplified configuration variables
    to deploy Cumulus VXLAN EVPN
    '''

    def __init__(self):
        # Check for overlapping interfaces
        CheckVars().interfaces

    def loopback_ips(self):
        '''
        Build a hosts loopback ips variable.

        Required variables in master.yml
        --------------------------------
        base_networks:
            loopbacks:
                spine: '192.168.0.0/25'
                edge: '192.168.0.128/25'
                border: '192.168.1.0/24'
                leaf: '192.168.2.0/23'
            vxlan_anycast: '192.168.8.0/23'

        Returns
        -------
        {
            "spine01": {
                "ip_addresses": [
                    "192.168.0.1/32"
                ],
                "clag_vxlan_anycast_ip": null
            },
            "leaf01": {
                "ip_addresses": [
                    "192.168.2.1/32"
                ],
                "clag_vxlan_anycast_ip": null
            }
        }
        '''
        # Check for overlapping networks
        base_networks = CheckVars().base_networks

        lo, clag = base_networks['loopbacks'], base_networks['vxlan_anycast']
        clag_net = Network(clag)

        loopback = {}
        for group, subnet in lo.items():
            lo_net = Network(subnet)
            for host in inventory.hosts(group):
                _host = Host(host)
                ips = {'ip_addresses': [], 'clag_vxlan_anycast_ip': None}

                lo_ip = lo_net.get_ip(_host.id, lo=True)
                ips['ip_addresses'].append(lo_ip)

                if host in inventory.hosts('leaf'):
                    ips['clag_vxlan_anycast_ip'] = (
                        clag_net.get_ip(_host.rack_id, addr=True)
                    )

                loopback[host] = ips

        return loopback

    def _vlans(self, key=None):
        '''
        Build a tenant vlans and l3vni variable.

        Required variables in master.yml
        --------------------------------
        vlans:
            tenant01:
            - { id: '100', name: 'vlan100'}
            tenant02:
            - { id: '500', name: 'vlan500'}

        Parameters
        ---------
        key: str
            valid options: ['vlan', 'id', tenant', 'name', 'type']
            Set the dict key of choice for easy reference of variable

        Returns
        -------
        if key is None:
        {
            "tenant01": [
                {
                    "id": "100",
                    "name": "vlan100"
                }
            ],
            "tenant02": [
                {
                    "id": "500",
                    "name": "vlan500"
                }
            ]
        }
        '''
        master_vlans = CheckVars().vlans

        def _l3vni():
            '''
            Generate a l3vni id each tenant and save it on l3vni.json file.

            Returns
            -------
            {
                "tenant01": {
                    "id": "4000",
                    "name": "l3vni",
                    "type": "l3",
                    "vlan": "vlan4000",
                    "tenant": "tenant01"
                },
                "tenant02": {
                    "id": "4001",
                    "name": "l3vni",
                    "type": "l3",
                    "vlan": "vlan4001",
                    "tenant": "tenant02"
                }
            }
            '''
            l3vni = File('l3vni')

            ids = [v['id'] for k, v in l3vni.data.items()]
            available_vnis = iter([
                r for r in range(4000, 4091) if str(r) not in ids
            ])

            for tenant in master_vlans.keys():
                if tenant not in l3vni.data.keys() and tenant != 'default':
                    vni = next(available_vnis)
                    vlan = 'vlan' + str(vni)
                    l3vni.data[tenant] = {
                        'id': str(vni), 'name': 'l3vni',
                        'type': 'l3', 'vlan': vlan, 'tenant': tenant
                    }

            for tenant in l3vni.data.copy().keys():
                if tenant not in master_vlans.keys():
                    del l3vni.data[tenant]

            return l3vni.dump()

        if key is not None:
            x = collections.defaultdict(list)
            for tenant, vlans in copy.deepcopy(master_vlans).items():
                for index, vlan in enumerate(vlans):
                    vlan.update({
                        'tenant': tenant, 'type': 'l2',
                        'vlan': 'vlan' + vlan['id'], 'index': index
                    })
                vlans.append(_l3vni()[tenant])
                for k, v in itertools.groupby(vlans, lambda x: x[key]):
                    x[k].extend(list(v))

            groupby = collections.defaultdict(dict)
            for k, v in x.items():
                if len(v) > 1:
                    for _k, _v in itertools.groupby(v, lambda x: x['id']):
                        for item in _v:
                            groupby[k][_k] = item
                else:
                    for item in v:
                        groupby[k] = item

            return groupby

        return master_vlans

    def mlag_peerlink(self):
        '''
        Build an mlag peerlink variable.

        Required variable in master.yml
        -------------------------------
        mlag_peerlink_interfaces: 'swp23-24'

        Returns
        -------
        {
            "leaf01": {
                "priority": "1000",
                "system_mac": "44:38:39:ff:00:ff",
                "interfaces": "swp23,swp24",
                "backup_ip": "192.168.2.2",
                "peer_ip": "169.254.1.2",
                "ip": "169.254.1.1/30"
            }
        }
        '''
        interfaces = CheckVars().mlag_peerlink_interfaces
        lo = self.loopback_ips()

        mlag_peerlink = {}
        for host in inventory.hosts('leaf'):
            _host = Host(host)
            backup_ip = lo[_host.peer_host]['ip_addresses'][0].split('/')[0]
            system_mac = MACAddr('44:38:39:FF:01:00') - _host.rack_id

            if _host.id % 2 == 0:
                clag_role = '2000'
                ip, peer_ip = '169.254.1.2/30', '169.254.1.1'
            else:
                clag_role = '1000'
                ip, peer_ip = '169.254.1.1/30', '169.254.1.2'

            mlag_peerlink[host] = {
                'priority': clag_role, 'system_mac': system_mac,
                'interfaces': interfaces, 'backup_ip': backup_ip,
                'peer_ip': peer_ip, 'ip': ip
            }

        return mlag_peerlink

    def mlag_bonds(self):
        '''
        Build a clag ids and bonds variable.

        Required variable in master.yml
        -------------------------------
        mlag_bonds:
            rack01:
            - { name: server01, members: 'swp1', vids: '100' }
            rack02:
            - { name: server02, members: 'swp1', vids: '500' }

        Returns
        -------
        {
            "leaf01": {
                "bonds": [
                    {
                        "name": "server01",
                        "vids": "100",
                        "clag_id": 1,
                        "tenant": "tenant01",
                        "members": "swp1,swp3",
                        "alias": "tenant01.rack01.1"
                    }
                ]
                "bridge": [
                    {
                        "mode": "access",
                        "vids": "100",
                        "bonds": "server01"
                    }
                ]
            }
        }
        '''
        mlag_bonds = CheckVars().mlag_bonds

        def _clag_interfaces():
            '''
            Generate a unique clag id of a bond and save it on
            'clag_interfaces.json' file.

            Returns
            -------
            {
                "rack01": {
                    "server01": 1
                },
                "rack02": {
                    "server01": 5
                }
            }
            '''
            clag_ifaces = File('clag_interfaces')

            for rack, bonds in mlag_bonds.items():
                try:
                    existing_ids = list(clag_ifaces.data[rack].values())
                except KeyError:
                    existing_ids = [0]
                    clag_ifaces.data[rack] = {}

                available_ids = iter(
                    [r for r in range(1, 200) if r not in existing_ids]
                )

                for index, bond in enumerate(bonds, start=1):
                    if bond['name'] not in clag_ifaces.data[rack].keys():
                        clag_ifaces.data[rack][bond['name']] = (
                            next(available_ids)
                        )

            for rack, bonds in clag_ifaces.data.copy().items():
                if rack in mlag_bonds.keys():
                    _bonds = [v['name'] for v in mlag_bonds[rack]]
                    for bond, _ in bonds.copy().items():
                        if bond not in _bonds:
                            del clag_ifaces.data[rack][bond]
                else:
                    del clag_ifaces.data[rack]

            return clag_ifaces.dump()

        clag_id = _clag_interfaces()
        master_vlans = self._vlans(key='id')

        rack_bonds = {}
        for rack, bonds in mlag_bonds.items():
            _bonds = []
            for bond in bonds:
                _vids = filter.uncluster(bond['vids'])
                for vid in _vids:
                    tenant = master_vlans[vid]['tenant']
                    break

                cid = clag_id[rack][bond['name']]
                vids = ','.join(filter.cluster(_vids))
                members = ','.join(filter.uncluster(bond['members']))
                alias = '{}.{}.{}'.format(tenant, rack, cid)
                _bonds.append({
                    'name': bond['name'], 'vids': vids, 'clag_id': cid,
                    'tenant': tenant, 'members': members, 'alias': alias
                })

            _bridge = collections.defaultdict(list)
            for k, v in itertools.groupby(_bonds, lambda x: x['vids']):
                for item in v:
                    _bridge[k].append(item['name'])
            bridge = []
            for k, v in _bridge.items():
                mode = 'access' if len(filter.uncluster(k)) == 1 else 'vids'
                bridge.append({'mode': mode, 'vids': k, 'bonds': ','.join(v)})

            rack_bonds[rack] = {'bonds': _bonds, 'bridge': bridge}

        host_bonds = {}
        for rack, bonds in rack_bonds.items():
            for host in Inventory().hosts('leaf'):
                _host = Host(host)
                if _host.rack == rack:
                    host_bonds[host] = bonds

        return host_bonds

    @property
    def _host_vlans(self):
        '''
        Return a list of all the vlans including l3vni assign to a host.
        Data is derive from 'self.mlag_bond' and 'self._vlans'.
        '''
        master_vlans = self._vlans(key='id')
        host_bonds = self.mlag_bonds()

        host_vlans = collections.defaultdict(list)
        for host, bonds in host_bonds.items():
            _vids = set([])
            for bond in bonds['bonds']:
                for vid in filter.uncluster(bond['vids']):
                    _vids.add(vid)

                for id, v in master_vlans.items():
                    if v['tenant'] == bond['tenant'] and v['type'] == 'l3':
                        _vids.add(id)

            for _vid in _vids:
                host_vlans[host].append(master_vlans[_vid])

        for host in inventory.hosts('border'):
            for id, v in master_vlans.items():
                if v['type'] == 'l3':
                    host_vlans[host].append(v)

        return host_vlans

    def vxlans(self):
        '''
        Build a vxlan variable. Data is derive from 'self._host_vlans'.

        Returns
        -------
        {
            "leaf01": {
                "local_tunnelip": "192.168.2.1",
                "vxlan_interfaces": [
                    {
                        "alias": "tenant01.4000.l3vni",
                        "name": "vni4000",
                        "vlan": "vlan4000",
                        "tenant": "tenant01",
                        "type": "l3",
                        "id": "4000",
                        "vid": "4000"
                    },
                    {
                        "alias": "tenant01.100.vlan100",
                        "name": "vni100",
                        "vlan": "vlan100",
                        "tenant": "tenant01",
                        "type": "l2",
                        "id": "100",
                        "vid": "100"
                    }
                ],
                "summary": "vni100,4000"
            }
        }
        '''
        base_name = 'vni'
        base_vxlan_id = 0
        host_vlans = self._host_vlans

        vxlans = {}
        for host, vlans in host_vlans.items():
            lo = self.loopback_ips()[host]['ip_addresses'][0].split('/')[0]
            vxlan_interfaces = []
            for vlan in vlans:
                alias = '{}.{}.{}'.format(
                    vlan['tenant'], vlan['id'], vlan['name']
                    )
                name = base_name + vlan['id']
                vxlan_id = str(base_vxlan_id + int(vlan['id']))
                vxlan_interfaces.append({
                    'alias': alias, 'name': name, 'vlan': vlan['vlan'],
                    'tenant': vlan['tenant'], 'type': vlan['type'],
                    'id': vxlan_id, 'vid': vlan['id']
                    })
            summary = filter.cluster(
                [i['name'] for i in vxlan_interfaces], group_name=True
                )
            vxlans[host] = {
                'local_tunnelip': lo, 'vxlan_interfaces': vxlan_interfaces,
                'summary': ''.join(summary)
                }

        return vxlans

    def l3vni(self):
        vxlans = self.vxlans()

        l3vni = {}
        for host, v in vxlans.items():
            _l3vni = {}
            for vxlan in v['vxlan_interfaces']:
                if vxlan['type'] == 'l3':
                    _l3vni[vxlan['tenant']] = vxlan['id']
            l3vni[host] = _l3vni
        return l3vni

    @property
    def _vlans_network(self):
        '''
        Generate a unique network prefix for each VLAN that do not have
        the 'network_prefix' or 'prefixlen' attribute. Data is save on
        'vlas_network.json' file.

        Required variables in master.yml
        --------------------------------
        vlans:
            tenant01:
            - { id: '100', name: 'vlan100'}
            tenant02:
            - { id: '500', name: 'vlan500'}

        base_networks:
          vlans: '172.16.0.0/14'

        Returns
        -------
        {
            "vlan100": {
                "id": "100",
                "name": "vlan100",
                "tenant": "tenant01",
                "type": "l2",
                "vlan": "vlan100",
                "allocation": "auto_network_prefix",
                "network_prefix": "172.16.0.0/24"
            },
            "vlan500": {
                "id": "500",
                "name": "vlan500",
                "tenant": "tenant02",
                "type": "l2",
                "vlan": "vlan500",
                "allocation": "auto_network_prefix",
                "network_prefix": "172.16.1.0/24"
            }
        }
        '''
        mv = self._vlans()
        vlans_network = File('vlans_network')
        vlans = self._vlans(key='vlan')

        for vlan, v in vlans_network.data.copy().items():
            # Delete VLANs IP network not in master file
            if vlan not in vlans:
                vlans_network.data.pop(vlan)

        existing_net_prefix = list(
            map(lambda x: x['network_prefix'], vlans_network.data.values())
        )

        checkvars = CheckVars()
        base_vlans_network = Network(checkvars.base_networks['vlans'])
        for vlan, v in vlans.items():
            if v['type'] == 'l2':
                if 'network_prefix' in v:
                    t = v['tenant']
                    allocation = 'manual'
                    if vlan not in vlans_network.data:
                        checkvars.vlans_network(
                            t, mv[t][v['index']], vlans_network.data
                        )
                    else:
                        if (vlans_network.data[vlan]['network_prefix']
                                != v['network_prefix']):
                            checkvars.vlans_network(
                                t, mv[t][v['index']], vlans_network.data
                            )
                            vlans_network.data[vlan].update({
                                'network_prefix': v['network_prefix'],
                                'allocation': 'manual'
                            })

                elif 'prefixlen' in v:
                    allocation = 'auto_prefixlen'
                    if vlan not in vlans_network.data:
                        subnet = base_vlans_network.get_subnet(
                            existing_net_prefix, prefixlen=v['prefixlen']
                        )
                        vlans_network.data[vlan] = {
                            'allocation': allocation,
                            'network_prefix': subnet
                            }

                    else:
                        if (vlans_network.data[vlan]['allocation']
                                != 'auto_prefixlen'):
                            subnet = base_vlans_network.get_subnet(
                                existing_net_prefix,
                                prefixlen=v['prefixlen']
                            )
                            vlans_network.data[vlan].update({
                                'network_prefix': subnet,
                                'allocation': 'auto_prefixlen'
                            })
                else:
                    allocation = 'auto_network_prefix'
                    if vlan not in vlans_network.data:
                        subnet = base_vlans_network.get_subnet(
                            existing_net_prefix
                        )
                        vlans_network.data[vlan] = {
                            'allocation': allocation,
                            'network_prefix': subnet
                            }
                    else:
                        if (vlans_network.data[vlan]['allocation']
                                != 'auto_network_prefix'):
                            subnet = base_vlans_network.get_subnet(
                                existing_net_prefix
                            )
                            vlans_network.data[vlan].update({
                                'network_prefix': subnet,
                                'allocation': 'auto_network_prefix'
                            })

        return vlans_network.dump()

    def vlans_interface(self):
        '''
        Build an SVI variable. Data is derived from 'self._vlans_network'.

        Returns
        -------
        {
            "leaf01": {
                "l2svi": [
                    {
                        "ip": "172.16.0.253/24",
                        "name": "vni100",
                        "vhwaddr": "44:38:39:ff:01:64",
                        "vid": "100",
                        "vip": "172.16.0.254/24",
                        "vlan": "vlan100",
                        "vrf": "tenant01"
                    },

                ],
                "l3svi": [
                     {
                        "router_mac": "44:39:39:ff:ff:fe",
                        "vid": "4000",
                        "vlan": "vlan4000",
                        "vni": "4000",
                        "vrf": "tenant01"
                    },
                ],
                "vids": [
                    "100",
                    "4000"
                ]
            }
        }
        '''
        vlans_network = self._vlans_network
        host_vlans = self._host_vlans

        vlans_interface = {}

        for host, vlans in host_vlans.items():
            svi = {'l2svi': [], 'l3svi': [], 'vids': []}
            _host = Host(host)

            for vlan in vlans:
                if vlan['type'] == 'l2':
                    network = Network(
                        vlans_network[vlan['vlan']]['network_prefix']
                        )
                    vhwaddr = (
                        MACAddr('44:38:39:FF:01:00') + int(vlan['id'])
                    )
                    vip = network.get_ip(0)
                    ip = network.get_ip(-_host.id)
                    svi['l2svi'].append({
                        'name': vlan['name'], 'ip': ip, 'vip': vip,
                        'vhwaddr': vhwaddr, 'vrf': vlan['tenant'],
                        'vlan': vlan['vlan'], 'vid': vlan['id']
                        })
                    svi['vids'].append(vlan['id'])
                else:
                    if host in inventory.hosts('leaf'):
                        router_mac = (
                            MACAddr('44:39:39:FF:FF:FF') - _host.rack_id
                        )
                        svi['l3svi'].append({
                            'router_mac': router_mac, 'vrf': vlan['tenant'],
                            'vlan': vlan['vlan'], 'vid': vlan['id'],
                            'vni': vlan['id']
                            })
                        svi['vids'].append(vlan['id'])
                    else:
                        svi['l3svi'].append({
                            'vrf': vlan['tenant'], 'vlan': vlan['vlan'],
                            'vid': vlan['id'], 'vni': vlan['id']
                            })
                        svi['vids'].append(vlan['id'])

            vlans_interface[host] = svi

        return vlans_interface

    def _ip_network_link_nodes(self, with_base_network=True):
        '''
        Build a base IP network links.

        Required variable in master.yml
        -------------------------------
        network_links:
          - name: external_connectivity
            links:
              - 'edge:eth0 -- border:swp1'
            interface_type: sub_interface

        base_networks:
          external_connectivity: '192.168.254.0/23'

        Returns
        -------
        if with_base_network:
        {
            "192.168.254.0/23": {
                "edge01:eth0 -- border01:swp1_4000": {
                    "vrf": "tenant01",
                    "nodes": [
                        {
                            "host": "edge01",
                            "interface": "eth0",
                            "neighbor": "border01",
                            "ngroup": "border",
                            "ninterface": "swp1"
                        },
                        {
                            "host": "border01",
                            "interface": "swp1",
                            "neighbor": "edge01",
                            "ngroup": "edge",
                            "ninterface": "eth0"
                        }
                    ]
                }
            }
        }
        else:
        {
            "edge01:eth1 -- border02:swp1_4001": {
                "vrf": "tenant02",
                "nodes": [
                    {
                        "host": "edge01",
                        "interface": "eth1",
                        "neighbor": "border02",
                        "ngroup": "border",
                        "ninterface": "swp1"
                    },
                    {
                        "host": "border02",
                        "interface": "swp1",
                        "neighbor": "edge01",
                        "ngroup": "edge",
                        "ninterface": "eth1"
                    }
                ]
            }
        }

        '''
        ip_network_type = ['ip', 'sub_interface']
        l3vni = {v['tenant']: v['id']
                 for k, v in self._vlans(key='vlan').items()
                 if v['type'] == 'l3'
                 }

        _ip_network_links = {}
        for nl in mf['network_links']:
            if nl['interface_type'] in ip_network_type:
                links = Link(nl['name'], nl['links'])
                base_network = CheckVars().link_base_network(nl['name'])
                link_nodes = links.link_nodes()

                _links = {}
                for link in links:
                    nodes = [node for node in link_nodes[link]]
                    if nl['interface_type'] == 'sub_interface':
                        try:
                            for item in nl['vifs']:
                                vrf = item['vrf'] if 'vrf' in item else None
                                _link = '{}_{}'.format(link, item['vid'])
                                _links[_link] = {'vrf': vrf, 'nodes': nodes}

                        except KeyError:
                            for vrf, vid in l3vni.items():
                                _link = '{}_{}'.format(link, vid)
                                _links[_link] = {'vrf': vrf, 'nodes': nodes}

                    elif nl['interface_type'] == 'ip':
                        vrf = nl['vrf'] if 'vrf' in nl else None
                        _links[link] = {'vrf': vrf, 'nodes': nodes}

                if with_base_network:
                    _ip_network_links[base_network] = _links
                else:
                    for k, v in _links.items():
                        _ip_network_links[k] = v

        return _ip_network_links

    @property
    def _ip_network_links(self):
        '''
        Generate a unique IP network /30 for point-to-point link that
        require a IP network and save it in 'ip_network_links.json' file.
        Data is derive from 'self._ip_network_link_nodes'.

        Returns
        -------
        {
            "edge01:eth0 -- border01:swp1_4000": "192.168.254.0/30"
        }
        '''
        ip_network_links = File('ip_network_links')
        link_network = ip_network_links.data
        ip_network_link_nodes = self._ip_network_link_nodes()

        nodes_link = [i for k, v in ip_network_link_nodes.items() for i in v]
        for link in link_network.copy():
            if link not in nodes_link:
                del link_network[link]

        existing_networks = list(link_network.values())
        for network, link_nodes in ip_network_link_nodes.items():
            net = Network(network)
            for link, nodes in link_nodes.items():
                if link not in link_network:
                    subnet = net.get_subnet(existing_networks, prefixlen=30)
                    link_network[link] = subnet

        return ip_network_links.dump()

    def ip_interfaces(self):
        '''
        Build an IP interfaces variable. Data is derive from
        'self._ip_network_link' and 'self._ip_network_link_nodes'

        Returns
        -------
        {
            "edge01": {
                "eth0.4000": {
                    "ip": "192.168.254.1/30",
                    "alias": "edge01:eth0 -- border01:swp1_4000",
                    "vrf": "tenant01",
                    "neighbor": {
                        "host": "border01",
                        "address": "192.168.254.2",
                        "interface": "swp1",
                        "group": "border"
                    }
                }
            },
            "border01": {
                "swp1.4000": {
                    "ip": "192.168.254.2/30",
                    "alias": "edge01:eth0 -- border01:swp1_4000",
                    "vrf": "tenant01",
                    "neighbor": {
                        "host": "edge01",
                        "address": "192.168.254.1",
                        "interface": "eth0",
                        "group": "edge"
                    }
                }
            }
        }
        '''
        ip_network_links = self._ip_network_links
        ip_network_link_nodes = (
            self._ip_network_link_nodes(with_base_network=False)
        )

        ip_interfaces = collections.defaultdict(dict)
        for link, v in ip_network_link_nodes.items():
            net = Network(ip_network_links[link])
            for idx, node in enumerate(v['nodes'], start=1):
                try:
                    vid = link.split('_')[1]
                    interface = '{}.{}'.format(node['interface'], vid)
                except IndexError:
                    interface = node['interface']

                ip = net.get_ip(idx)
                nip = net.get_ip(idx-1, addr=True)
                ip_interfaces[node['host']][interface] = {
                    'ip': ip, 'alias': link, 'vrf': v['vrf'],
                    'neighbor': {
                        'host': node['neighbor'], 'address': nip,
                        'interface': node['ninterface'],
                        'group': node['ngroup']
                    }
                }

        master_ip_interfaces = mf['ip_interfaces']
        for host in master_ip_interfaces:
            for interface, v in master_ip_interfaces[host].items():
                ip_interfaces[host][interface] = {
                    'ip': v['address'], 'alias': v['desc'],
                    'vrf': 'default', 'neighbor': None
                }

        interface_sort = {
            k: dict(collections.OrderedDict(
                    sorted(v.items(), key=lambda x: filter.natural_keys(x[0]))
                    )) for k, v in ip_interfaces.items()
        }

        return interface_sort

    def unnumbered_interfaces(self):
        '''
        Build a unnumbered interfaces.

        Required variable in master.yml
        -------------------------------
        network_links:
          - name: fabric
            links:
              - 'spine:swp1 -- leaf:swp21'
              - 'spine:swp23 -- border:swp23'
            interface_type: unnumbered

        Returns
        -------
        {
            "spine01": {
                "swp1": {
                    "alias": "spine01:swp1 -- leaf01:swp21",
                    "vrf": "default",
                    "neighbor": {
                        "host": "leaf01",
                        "interface": "swp21",
                        "group": "leaf"
                    }
                }
            },
            "leaf01": {
                "swp21": {
                    "alias": "spine01:swp1 -- leaf01:swp21",
                    "vrf": "default",
                    "neighbor": {
                        "host": "spine01",
                        "interface": "swp1",
                        "group": "spine"
                    }
                }
            }
        }
        '''
        unnumbered_interfaces = collections.defaultdict(dict)
        for nl in mf['network_links']:
            if nl['interface_type'] == 'unnumbered':
                links = Link(nl['name'], nl['links'])
                link_nodes = links.link_nodes()
                vrf = nl['vrf'] if 'vrf' in nl else 'default'

                for link, nodes in link_nodes.items():
                    for node in nodes:
                        host, interface = node['host'], node['interface']
                        unnumbered_interfaces[host][interface] = {
                            'alias': link, 'vrf': vrf,
                            'neighbor': {
                                'host': node['neighbor'],
                                'interface': node['ninterface'],
                                'group': node['ngroup']
                            }
                        }

        interface_sort = {
            k: collections.OrderedDict(
                    sorted(v.items(), key=lambda x: filter.natural_keys(x[0]))
                ) for k, v in unnumbered_interfaces.items()
        }

        return interface_sort

    def bgp_neighbors(self):
        '''
        Generate a BGP neighbors variable. Data is derive from
        'self.ip_interfaces' and 'self.unnumbered_interfaces'

        Returns
        -------
        {
            "border01": {
                "tenant01": {
                    "router_id": "192.168.1.1",
                    "as": 64552,
                    "neighbors": [
                        {
                            "neighbor": "192.168.254.1",
                            "remote_as": 64531,
                            "remote_id": "192.168.0.129",
                            "peer_group": "edge",
                            "remote_host": "edge01"
                            "remote_interface": "eth0",
                            "local_interface": "swp1.4000"
                        }
                    ],
                    "peer_groups": [
                        "edge"
                    ]
                },
                "default": {
                    "router_id": "192.168.1.1",
                    "as": 64552,
                    "neighbors": [
                        {
                            "neighbor": "swp23",
                            "remote_as": "external",
                            "remote_id": "192.168.0.1",
                            "peer_group": "spine",
                            "remote_host": "spine01"
                            "remote_interface": "swp23",
                            "local_interface": "swp23"
                        }
                    ],
                    "peer_groups": [
                        "spine"
                    ]
                }
            }
        }
        '''
        bgp_config = {}
        base_asn = CheckVars().base_asn
        for group, asn in base_asn.items():
            for host in inventory.hosts(group):
                _host = Host(host)
                lo = self.loopback_ips()[host]['ip_addresses'][0]
                router_id = lo.split('/')[0]
                _asn = asn if group == 'spine' else asn + _host.id
                bgp_config[host] = {'as': _asn, 'router_id': router_id}

        ifaces = [self.ip_interfaces(), self.unnumbered_interfaces()]
        _ifaces = collections.defaultdict(dict)
        for item in ifaces:
            for k, v in item.items():
                _ifaces[k].update(v)

        bgp_neighbors = collections.defaultdict(dict)
        for host, ifaces in _ifaces.items():
            neighbors, vrf, peer_groups = (
                collections.defaultdict(list), {}, set([])
                )
            for iface, v in ifaces.items():
                if v['neighbor'] is not None:
                    n = v['neighbor']
                    remote_id = bgp_config[n['host']]['router_id']
                    if 'ip' not in v:
                        remote_as = 'external'
                        nei = iface
                    else:
                        remote_as = bgp_config[n['host']]['as']
                        nei = n['address']

                    vrf[v['vrf']] = {
                        'router_id': bgp_config[host]['router_id'],
                        'as': bgp_config[host]['as']
                    }
                    neighbors[v['vrf']].append({
                        'neighbor': nei, 'remote_as': remote_as,
                        'remote_id': remote_id, 'peer_group': n['group'],
                        'remote_host': n['host'],
                        'remote_interface': n['interface'],
                        'local_interface': iface
                    })

            for _vrf, v in neighbors.items():
                peer_groups = [k for k, v in itertools.groupby(
                    v, lambda x: x['peer_group']
                    )]
                vrf[_vrf].update({
                    'neighbors': neighbors[_vrf],
                    'peer_groups': peer_groups
                    })

            bgp_neighbors[host] = vrf

        return dict(bgp_neighbors)

    @property
    def _nat_rules(self):
        '''
        Generate a NAT rules and save it on nat_rules.json file.

        Required variables in master.yml
        --------------------------------
        vlans:
            tenant01:
              - id: '500'
                name: 'vlan500'
                prefixlen: 20
                allow_nat: true

        base_networks:
          oob_management: '172.24.0.0/24'

        Returns
        -------
        {
            "1": {
                "name": "oob_management",
                "tenant": "default",
                "source_address": "172.24.0.0/24"
            },
            "5000": {
                "name": "vlan500",
                "tenant": "tenant01",
                "source_address": "172.16.0.0/24"
            }
        }
        '''
        nat_rules = File('nat_rules')
        available_rules = iter([
            r for r in range(500, 600, 10) if str(r) not in nat_rules.data
        ])
        vlans = self._vlans(key='vlan')
        vlans_network = self._vlans_network
        nat_networks = {k: v for k, v in vlans.items() if 'allow_nat' in v}
        network_prefixes = [
            vlans_network[k]['network_prefix']
            for k, _ in nat_networks.items()
            ]
        source_addresses = [
            v['source_address'] for k, v in nat_rules.data.items()
            ]

        # Add nat rule for oob-management network
        oob_mgmt_network = CheckVars().base_networks['oob_management']
        nat_rules.data['1'] = {
            'name': 'oob_management',
            'tenant': 'default', 'source_address': oob_mgmt_network
            }

        for k, v in nat_rules.data.copy().items():
            if v['source_address'] not in network_prefixes and k != '1':
                del nat_rules.data[k]

        for k, v in nat_networks.items():
            source_address = vlans_network[k]['network_prefix']
            if source_address not in source_addresses:
                rule = next(available_rules)
                nat_rules.data[rule] = {
                    'name': vlans[k]['name'],
                    'tenant': vlans[k]['tenant'],
                    'source_address': source_address
                }

        for k, v in nat_rules.data.items():
            for k1, v1 in vlans_network.items():
                if v1['network_prefix'] == v['source_address']:
                    nat_rules.data[k].update({
                        'name': vlans[k1]['name'],
                        'tenant': vlans[k1]['tenant']
                    })

        return nat_rules.dump()

    def nat(self):
        '''
        Build a host NAT variable.

        Required variables in master.yml
        --------------------------------
        ip_interfaces:
            edge01:
                eth3:
                    address: dhcp
                    ip_nat: outside
                eth2: # Management interface
                    address: '172.24.0.254/24'

        Returns
        -------
        {
            "edge01": [
                {
                    "interface": "eth3",
                    "name": "oob_management",
                    "rule": 1,
                    "tenant": "default",
                    "source_address": "172.24.0.0/24"
                },
                {
                    "interface": "eth3",
                    "name": "vlan500",
                    "rule": 5000,
                    "tenant": "tenant01",
                    "source_address": "172.16.0.0/24"
                }
            ]
        }
        '''
        ip_interfaces = File().master()['ip_interfaces']
        nat_rules = self._nat_rules

        nat_host = collections.defaultdict(list)
        for host, interfaces in ip_interfaces.items():
            nat_ifaces = []
            for iface, v in interfaces.items():
                if 'ip_nat' in v and v['ip_nat'] == 'outside':
                    nat_ifaces.append(iface)
            for index, nat_iface in enumerate(nat_ifaces):
                for k, v in nat_rules.items():
                    rule = int(k) + index
                    nat_host[host].append({
                        'interface': nat_iface, 'name': v['name'],
                        'rule': rule, 'tenant': v['tenant'],
                        'src_addr': v['source_address']
                        })

        return dict(nat_host)
