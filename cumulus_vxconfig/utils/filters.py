import collections
import itertools
import operator
import re

import ruamel.yaml


class Filters:

    def natural_keys(self, v):

        def convert(v):
            return int(v) if v.isdigit() else v

        return [convert(c) for c in re.split('(\\d+)', v)]

    def yaml_format(self, data, style="", flow=None, start=True):
        return ruamel.yaml.dump(
            data, Dumper=ruamel.yaml.RoundTripDumper,
            block_seq_indent=2, indent=4,
            default_flow_style=flow, default_style=style,
            explicit_start=start,
            )

    def combine(list_of_dicts):
        x = collections.defaultdict(dict)
        for item in list_of_dicts:
            for k, v in item.items():
                x[k].update(v)
        return x

    def _un_cluster(self, v, cluster=False):
        '''
        Cluster items or list of individual items.

        Parameters
        ---------
        items:
            list: ['swp1', 'swp2', 'swp4', 'swp5', 'swp10-11']
            str: 'swp1, swp2, swp4, swp5, swp10-11'
        cluster:
            bool

        Returns
        -------
        if cluster:
            ['swp1-2', 'swp4-5', 'swp10-11']
        else:
            ['swp1', 'swp2', 'swp4', 'swp5', 'swp10', 'swp11']
        '''
        _uncluster = []
        for item in v:
            li = re.split('(\\d+)', item)
            if len(li) == 1:
                raise ValueError('Invalid value: ' + item)

            name, id, *r = li
            if len(li) == 3:
                _uncluster.append((name, int(id)))
            else:
                start, end = int(id), int(r[1])
                for n in range(start, end + 1):
                    _uncluster.append((name, n))

        _cluster = []
        for k, v in itertools.groupby(_uncluster, key=lambda x: x[0]):
            ids = list(map(operator.itemgetter(1), v))
            for _k, _v in itertools.groupby(
                    enumerate(sorted(ids)), lambda x: x[1]-x[0]):
                group = list(map(operator.itemgetter(1), list(_v)))
                if len(group) > 1:
                    _cluster.append("{}{}-{}".format(k, group[0], group[-1]))
                else:
                    _cluster.append("{}{}".format(k, group[0]))

        if not cluster:
            x = ['{}{}'.format(item[0], item[1]) for item in _uncluster]
            return sorted(x, key=self.natural_keys)

        return sorted(_cluster, key=self.natural_keys)

    def uncluster(self, v):
        if isinstance(v, list):
            x = v
        elif isinstance(v, str):
            x = [i.strip() for i in v.split(',')]
        return self._un_cluster(x)

    def cluster(self, v, group_name=False):
        if isinstance(v, list):
            x = v
        elif isinstance(v, str):
            x = [i.strip() for i in v.split(',')]

        cluster = self._un_cluster(x, cluster=True)
        if group_name:
            _name = collections.defaultdict(list)
            for item in cluster:
                li = re.split('(\\d+)', item)
                name, *r = li
                _name[name].append(''.join(r))

            return ['{}{}'.format(k, ','.join(v)) for k, v in _name.items()]

        return cluster

    def default_to_dict(self, d):
        if isinstance(d, collections.defaultdict):
            d = {k: self.default_to_dict(v) for k, v in d.items()}
        return d
