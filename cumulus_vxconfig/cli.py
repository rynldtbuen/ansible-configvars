import argparse
import json
from cumulus_vxconfig.configvars import ConfigVars

configvars = ConfigVars()
dirs = dir(configvars)

methods = []
for item in dirs:
    if (hasattr(getattr(configvars, item), '__call__')
            and not item.startswith('_')):
        methods.append(item)


def main():
    parser = argparse.ArgumentParser(
        description="Command line tool to print configuration variables."
    )
    parser.add_argument(
        "--config",
        "-c",
        dest="configvar",
        action="store",
        help="Name of configuration variable.",
    )

    parser.add_argument(
        "--list",
        dest="config_list",
        action="store_true",
        help="List of configuration variables.",
    )

    config = parser.parse_args()

    if config.config_list:
        print('\nConfiguration variables')
        print('=======================')
        print('{}\n'.format('\n'.join(methods)))
    elif config.configvar:
        method = getattr(configvars, config.configvar)
        try:
            print(json.dumps(method(), indent=4))
        except json.decoder.JSONDecodeError:
            print(method())
        except TypeError:
            print(method())


if __name__ == "__main__":
    main()
