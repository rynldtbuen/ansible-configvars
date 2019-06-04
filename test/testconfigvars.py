import argparse
import json
from cl_vx_config.configvars import ConfigVars

cl = ConfigVars()

parser = argparse.ArgumentParser(
    prog='testconfigvars',
    usage='%(prog)s [variable_name]',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=(
        '''
        variable_name valid options:
            [bgp_neighbors, loopback_ips, mlag_bonds, mlag_peerlink,
            vxlans, ip_interfaces, unnumbered_interfaces, vlans_interface]
        '''
    )
)

parser.add_argument(
    'variable_name',
    type=str,
    help='Name of configuration variable'
)

config = parser.parse_args()
method = getattr(cl, config.variable_name)

try:
    print(json.dumps(method(), indent=4))
except json.decoder.JSONDecodeError:
    print(method())
except TypeError:
    print(method())
