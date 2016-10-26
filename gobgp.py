# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from base import *

class GoBGP(Container):
    def __init__(self, name, host_dir, guest_dir='/root/config', image='bgperf/gobgp'):
        super(GoBGP, self).__init__(name, image, host_dir, guest_dir)

    @classmethod
    def build_image(cls, force=False, tag='bgperf/gobgp', checkout='HEAD', nocache=False):
        cls.dockerfile = '''
FROM golang:1.6
WORKDIR /root
RUN go get -v github.com/osrg/gobgp/gobgpd
RUN go get -v github.com/osrg/gobgp/gobgp
RUN cd $GOPATH/src/github.com/osrg/gobgp && git checkout {0}
RUN go install github.com/osrg/gobgp/gobgpd
RUN go install github.com/osrg/gobgp/gobgp
'''.format(checkout)
        super(GoBGP, cls).build_image(force, tag, nocache)


    def write_config(self, conf, name='gobgpd.conf'):
        config = {}
        config['global'] = {
            'config': {
                'as': conf['target']['as'],
                'router-id': conf['target']['router-id']
            },
        }
        if 'policy' in conf:
            config['policy-definitions'] = []
            config['defined-sets'] = {
                    'prefix-sets': [],
                    'bgp-defined-sets': {
                        'as-path-sets': [],
                        'community-sets': [],
                        'ext-community-sets': [],
                    },
            }
            for k, v in conf['policy'].iteritems():
                conditions = {
                    'bgp-conditions': {},
                }
                for i, match in enumerate(v['match']):
                    n = '{0}_match_{1}'.format(k, i)
                    if match['type'] == 'prefix':
                        config['defined-sets']['prefix-sets'].append({
                            'prefix-set-name': n,
                            'prefix-list': [{'ip-prefix': p} for p in match['value']]
                        })
                        conditions['match-prefix-set'] = {'prefix-set': n}
                    elif match['type'] == 'as-path':
                        config['defined-sets']['bgp-defined-sets']['as-path-sets'].append({
                            'as-path-set-name': n,
                            'as-path-list': match['value'],
                        })
                        conditions['bgp-conditions']['match-as-path-set'] = {'as-path-set': n}
                    elif match['type'] == 'community':
                        config['defined-sets']['bgp-defined-sets']['community-sets'].append({
                            'community-set-name': n,
                            'community-list': match['value'],
                        })
                        conditions['bgp-conditions']['match-community-set'] = {'community-set': n}
                    elif match['type'] == 'ext-community':
                        config['defined-sets']['bgp-defined-sets']['ext-community-sets'].append({
                            'ext-community-set-name': n,
                            'ext-community-list': match['value'],
                        })
                        conditions['bgp-conditions']['match-ext-community-set'] = {'ext-community-set': n}

                config['policy-definitions'].append({
                    'name': k,
                    'statements': [{'name': k, 'conditions': conditions, 'actions': {'route-disposition': {'accept-route': True}}}],
                })


        def gen_neighbor_config(n):
            c = {'config': {'neighbor-address': n['local-address'].split('/')[0], 'peer-as': n['as']}}

            if 'route_reflector' in n and n['route_reflector']:
                c['route-reflector'] = {'config': {'route-reflector-client': True,
                                                   'route-reflector-cluster-id': conf['target']['router-id']}}
            else:
                c['route-server'] = {'config': {'route-server-client': True}}
                c['transport'] = {'config': {'local-address': conf['target']['local-address'].split('/')[0]}}

            if 'filter' in n:
                a = {}
                if 'in' in n['filter']:
                    a['in-policy-list'] = n['filter']['in']
                    a['default-in-policy'] = 'accept-route'
                if 'out' in n['filter']:
                    a['export-policy-list'] = n['filter']['out']
                    a['default-export-policy'] = 'accept-route'
                c['apply-policy'] = {'config': a}
            return c

        neighbors = conf['tester'].values() + [conf['monitor']]
        if 'target-sub' in conf:
            neighbors = neighbors + [conf['target-sub']]

        config['neighbors'] = [gen_neighbor_config(n) for n in neighbors]
        with open('{0}/{1}'.format(self.host_dir, name), 'w') as f:
            f.write(yaml.dump(config, default_flow_style=False))
        self.config_name = name

    def run(self, conf, brname=''):
        ctn = super(GoBGP, self).run(brname)

        if self.config_name == None:
            self.write_config(conf)

        startup = '''#!/bin/bash
ulimit -n 65536
ip a add {0} dev eth1
gobgpd -t yaml -f {1}/{2} -l {3} > {1}/gobgpd.log 2>&1
'''.format(conf['target']['local-address'], self.guest_dir, self.config_name, 'info')
        filename = '{0}/start.sh'.format(self.host_dir)
        with open(filename, 'w') as f:
            f.write(startup)
        os.chmod(filename, 0777)
        i = dckr.exec_create(container=self.name, cmd='{0}/start.sh'.format(self.guest_dir))
        dckr.exec_start(i['Id'], detach=True, socket=True)

        return ctn
