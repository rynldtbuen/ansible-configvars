import argparse
import json
from cl_vx_config.configvars import ConfigVars

cl = ConfigVars()

parser = argparse.ArgumentParser(
    prog='configvars',
    usage='%(prog)s --config [config_var]'
)

parser.add_argument(
    '--config',
    dest='config_var',
    help='name configuration variable',
)

parser.add_argument(
    '--config_list',
    action='store_true',
    help='list of configuration variables',
)

config = parser.parse_args()

if config.config_list:
    x = [
        'bgp_neighbors',
        'loopback_ips',
        'mlag_bonds',
        'mlag_peerlink',
        'ip_interfaces',
        'unnumbered_interfaces',
        'vxlans',
        'vlans_interface'
    ]
    print(x)

elif config.config_var:
    try:
        method = getattr(cl, config.config_var)
        try:
            print(json.dumps(method(), indent=4))
        except json.decoder.JSONDecodeError:
            print(method())
        except TypeError:
            print(method())
    except AttributeError:
        print('config_var: {} not found'.format(config.config_var))
