import collections
import json
import functools
import itertools
import os
import re
import yaml

import netaddr
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.errors import AnsibleError

from cumulus_vxconfig.utils.filters import Filters

filter = Filters()


class File:

    def __init__(self, fname=None):

        user = os.environ.get('USER')
        config_dir = "/home/{}/.cumulus_vxconfig".format(user)

        try:
            os.makedirs(config_dir)
        except FileExistsError:
            pass

        if fname is not None:

            self.fname = fname
            self.path = '{}/{}.json'.format(config_dir, fname)

            if not os.path.isfile(self.path):
                with open(self.path, 'w') as f:
                    json.dump({}, f)

            with open(self.path, 'r') as f:
                self.data = json.load(f)

    def dump(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)
        return self.data

    def master(self):
        path = os.getcwd() + '/master.yml'

        with open(path, 'r') as f:
            return yaml.safe_load(f)

    @property
    def default(self):
        base_network = self.master['base_networks']
        default = {
            'clag_interfaces': {},
            'external_networks': {
                'base_network': base_network['external_connectivity'],
                'networks': {}
            },
            'vlans_network': {
                'base_network': base_network['vlans'],
                'networks': {}
            },
            'l3vni': {}
        }

        return default[self.fname]


class Interface:

    def __init__(self, interface):
        self.interface = interface

        try:
            base_name = (
                re.search(r'(\w+|\d+)(?<!\d)', self.interface).group(0)
            )
        except AttributeError:
            base_name = ''
        except TypeError:
            base_name = ''

        self.base_name = base_name

        id = str(self.interface).replace(self.base_name, '')

        if id.isdigit():
            self.id = int(id)
        if '-' in id:
            self.id = id
        if not id:
            raise AnsibleError('Invalid interface: ' + self.interface)

    def __repr__(self):
        return self.interface

    def __add__(self, num):
        return '{}-{}'.format(self.interface, self.id + num - 1)


class Network(netaddr.IPNetwork):

    def __init__(self, addr):
        super().__init__(addr)

        if self.network != self.ip:
            raise AnsibleError('Invalid network: ' + self.__str__())

    def __len__(self):
        return len(list(self.iter_hosts()))

    def __iter__(self):
        ''' Return a list of usable IP address '''
        for item in self.iter_hosts():
            yield '{}/{}'.format(item, self.prefixlen)

    def __next__(self):
        yield self.__iter__()

    def get_subnet(self, existing_networks, prefixlen=24):
        ''' Get a unique subnet of a network given an existing networks '''
        available_networks = (
            netaddr.IPSet(self.cidr) - netaddr.IPSet(
                netaddr.cidr_merge([Network(net) for net in existing_networks])
            )
        )
        while len(available_networks.iter_cidrs()) > 0:
            for net in available_networks.iter_cidrs():
                for subnet in net.subnet(prefixlen, count=1):
                    existing_networks.append(str(subnet))
                    return str(subnet)
        else:
            raise AnsibleError('Run out of subnets')

    def _subnet(self, existing_networks, prefixlen=24):
        ''' Get a unique subnet of a network given an existing networks '''
        available_networks = (
            netaddr.IPSet(self.cidr) - netaddr.IPSet(
                netaddr.cidr_merge([Network(net) for net in existing_networks])
            )
        )
        while len(available_networks.iter_cidrs()) > 0:
            for net in available_networks.iter_cidrs():
                for subnet in net.subnet(prefixlen, count=1):
                    existing_networks.append(str(subnet))
                    yield str(subnet)
        else:
            raise AnsibleError('Run out of subnets')

    def get_ip(self, index, lo=False, addr=False):
        ''' Return an IP address given index '''
        try:
            ip_addr = list(self.__iter__())[index - 1]
            if lo:
                return ip_addr.replace(str(self.prefixlen), '32')
            elif addr:
                return ip_addr.split('/')[0]
            else:
                return ip_addr
        except IndexError:
            err = True
        else:
            err = False

        if err:
            raise AnsibleError('Run out of IP addresses')

    def overlaps(self, other):
        ''' Return True if one IP network overlaps with other IP network '''
        return self.__contains__(other)

    @property
    def id(self):
        ''' Return a base int value of the IP network '''
        return re.search(r'^\d{2}', str(self.value)).group(0)

    @property
    def iprange(self):
        return netaddr.IPSet(self.cidr).iprange()


class MACAddr(netaddr.EUI):

    def __init__(self, addr):
        super().__init__(addr, dialect=netaddr.mac_unix_expanded)

    def __add__(self, index):
        return MACAddr(self.value + index).__str__()

    def __sub__(self, index):
        return MACAddr(self.value - index).__str__()


class Host:

    def __init__(self, host):
        self.host = host

        if self.host not in Inventory().hosts():
            raise AnsibleError('Host not found: ' + self.host)

        self.id = int(re.split('(\\d+)', self.host)[-2])

        if self.id % 2 == 0:
            rack_id = int(self.id - (self.id / 2))
        else:
            rack_id = int((self.id + 1) - (self.id + 1)/2)

        self.rack_id = rack_id

        self.rack = 'rack0' + str(self.rack_id)

    def __repr__(self):
        return self.host

    @property
    def peer_host(self):
        i = Inventory()
        for host in i.hosts():
            if host != 'localhost' and host != self.host:
                _host = Host(host)
                primary_group = i.groups(host, primary=True)
                if _host.rack_id == self.rack_id and (
                    primary_group == i.groups(self.host, primary=True)
                ):
                    return host


class Inventory:

    def __init__(self):

        self.inventory_source = os.getcwd() + '/devices'
        self.loader = DataLoader()

        self.inventory = InventoryManager(
            loader=self.loader, sources=[self.inventory_source]
        )

    def __iter__(self):
        return iter([h for h in self.hosts() if h != 'localhost'])

    def _check_host(self, host):
        if host not in self.__iter__():
            raise AnsibleError(host + ' not found')

    def hosts(self, pattern='all'):
        try:
            return self.inventory.get_groups_dict()[pattern]
        except KeyError:
            self._check_host(pattern)
            return [pattern]

    def groups(self, host, primary=True):
        self._check_host(host)
        groups = []
        for k, v in self.inventory.get_groups_dict().items():
            if host in v and k != 'all':
                if primary:
                    return k
                else:
                    groups.append(k)
        return groups

    def group_names(self):
        return [k for k in self.inventory.get_groups_dict()]


class Link:
    '''
    A Class take a dict with key as a variable name
    and values of list of link:
    fabric:
      - 'spine:swp1 -- leaf:swp21'
      - 'spine:swp23 -- border:swp23'
    '''
    def __init__(self, variable, _links):
        self.links = _links
        self.var = variable

        self.check_overlapping_interfaces

    def _link(self, __link, item_id=False):
        links = itertools.permutations(
            [item.strip() for item in __link.split('--')]
        )

        for index, link in enumerate(links):
            _link = [_l for l in link for _l in l.split(':')]

            dev_a, a_port, dev_b, b_port = _link

            data = (
                sorted(Inventory().hosts(dev_a)),
                filter.uncluster(
                    Interface(a_port) + len(Inventory().hosts(dev_b))
                    ),
                sorted(Inventory().hosts(dev_b)),
                filter.uncluster(
                    Interface(b_port) + len(Inventory().hosts(dev_a)),
                )
            )

            hosts, ports, neighbors, neighbors_port = data

            for host in range(len(hosts)):
                for neighbor in range(len(neighbors)):
                    connections = (
                        hosts[host], ports[neighbor],
                        neighbors[neighbor], neighbors_port[host]
                    )
                    if index == 0:
                        _item_id = '{} --> {}:{} -- {}:{}'.format(
                            __link,
                            dev_a, ''.join(filter.cluster(ports)),
                            dev_b, ''.join(filter.cluster(neighbors_port))
                            )

                        net_id = '{0}:{1} -- {2}:{3}'.format(*connections)
                    else:
                        net_id = '{2}:{3} -- {0}:{1}'.format(*connections)

                    if item_id:
                        yield dev_a, connections[1], _item_id
                    else:
                        yield connections, net_id

    def _group(self, host):
        return Inventory().groups(host)

    def __iter__(self):
        ''' Return values:
        [
            "spine02:swp3 -- leaf03:swp22",
            "spine02:swp4 -- leaf04:swp22",
            "spine02:swp2 -- leaf02:swp22",
            "spine01:swp23 -- border01:swp23",
            "spine01:swp24 -- border02:swp23",
            "spine02:swp1 -- leaf01:swp22",
            "spine02:swp24 -- border02:swp24",
            "spine01:swp4 -- leaf04:swp21",
            "spine01:swp3 -- leaf03:swp21",
            "spine01:swp2 -- leaf02:swp21",
            "spine02:swp23 -- border01:swp24",
            "spine01:swp1 -- leaf01:swp21"
        ]
        '''
        s = set([])
        for link in self.links:
            links = self._link(link)
            for item in links:
                s.add(item[1])
        return iter(sorted(s))

    @functools.lru_cache(maxsize=128)
    def link_nodes(self):
        ''' Return values:
        {
            "spine01:swp1 -- leaf01:swp21": [
                {
                    "host": "spine01",
                    "interface": "swp1",
                    "neighbor": "leaf01",
                    "ngroup": "leaf",
                    "ninterface": "swp21"
                },
                {
                    "host": "leaf01",
                    "interface": "swp21",
                    "neighbor": "spine01",
                    "ngroup": "spine",
                    "ninterface": "swp1"
                }
            ]
        }
        '''
        link_nodes = collections.defaultdict(list)
        for link in self.links:
            links = self._link(link)
            for item in links:
                host, port, nei, nei_port = item[0]
                link_nodes[item[1]].append({
                    'host': host, 'interface': port,
                    'neighbor': nei, 'ngroup': self._group(nei),
                    'ninterface': nei_port
                })
        return link_nodes

    @functools.lru_cache(maxsize=128)
    def device_interfaces(self):
        ''' Return values:
        {
            "spine": [
                [
                    "swp1",
                    "spine:swp1 -- leaf:swp21 --> spine:['swp1', 'swp2',
                    'swp3', 'swp4'] -- leaf:['swp21', 'swp22']"
                ],
                [
                    "swp2",
                    "spine:swp1 -- leaf:swp21 --> spine:['swp1', 'swp2',
                    'swp3', 'swp4'] -- leaf:['swp21', 'swp22']"
                ]
            ]
        }
        '''
        device_interfaces = collections.defaultdict(set)
        for idx, link in enumerate(self.links):
            links = self._link(link, item_id=True)
            for item in links:
                dev, port, item_link = item
                device_interfaces[dev].add(
                    (port, item_link, 'network_links', self.var)
                    )

        hosts = [h for h in device_interfaces if h in Inventory().hosts()]
        for host in hosts:
            x = device_interfaces[host]
            for k, v in device_interfaces.items():
                if host in Inventory().hosts(k):
                    device_interfaces[host] = device_interfaces[k] | x

        interfaces_links = {}
        for k, v in device_interfaces.items():
            interfaces_links[k] = list(v)

        return interfaces_links

    @property
    def check_overlapping_interfaces(self):
        mf = File().master()

        def items(error):
            for item in mf['network_links']:
                if item['name'] == self.var:
                    item['links'] = list(error)
                    return filter.yaml_format({'network_links': [item]})

        for item in itertools.combinations(self.links, 2):
            link_a, link_b = item
            if link_a == link_b:
                msg = ("Duplicate link: '{}'\n"
                       "Refer to the errors below and to your "
                       "'master.yml' file.\n{}")
                raise AnsibleError(msg.format(link_a, items(item)))

        interfaces_link = self.device_interfaces()
        for k, v in interfaces_link.items():
            for link in itertools.combinations(v, 2):
                link_a, link_b = link
                if link_a[0] == link_b[0]:
                    error = link_a[1], link_b[1]
                    msg = ("Overlapping link interfaces: '{} in {}'\n"
                           "Refer to the errors below and to your "
                           "'master.yml' file.\n{}")

                    raise AnsibleError(msg.format(link_a[0], k, items(error)))
