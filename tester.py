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

from exabgp import ExaBGP
import os
from  settings import dckr

def rm_line():
    print '\x1b[1A\x1b[2K\x1b[1D\x1b[1A'


class Tester(ExaBGP):
    def __init__(self, name, host_dir):
        super(Tester, self).__init__(name, host_dir)

    def run(self, conf, brname=''):
        super(Tester, self).run(brname)

        startup = ['''#!/bin/bash
ulimit -n 65536''']

        peers = conf['tester'].values()

        for i, p in enumerate(peers):
            with open('{0}/{1}.conf'.format(self.host_dir, p['router-id']), 'w') as f:
                local_address = p['local-address'].split('/')[0]
                config = '''neighbor {0} {{
    peer-as {1};
    router-id {2};
    local-address {3};
    local-as {4};
    static {{
'''.format(conf['target']['local-address'].split('/')[0], conf['target']['as'],
               p['router-id'], local_address, p['as'])
                f.write(config)
                for path in p['paths']:
                    if conf.mpls:
                        #route 10.0.0.0/24 rd 65000:1 next-hop 200.10.0.101 extended-community [ 0x0002fde800000001 0x0002271000000001 ] label 1000 split /25 ;
                        f.write('      route {0} rd {1}:{2} next-hop {3} extended-community [ 0x0002fde800000001 0x0002271000000001 ] label {4} split /25 ;\n'.format(path, p['as'], (1000+i), local_address, (1000+i)))
                    else
                        f.write('      route {0} next-hop {1};\n'.format(path, local_address))
                f.write('''   }
}
''')

                if 'target-sub' in conf:
                    config = '''neighbor {0} {{
    peer-as {1};
    router-id {2};
    local-address {3};
    local-as {4};
    static {{
'''.format(conf['target-sub']['local-address'].split('/')[0], conf['target-sub']['as'],
                    p['router-id'], local_address, p['as'])
                    f.write(config)
                    for path in p['paths']:
                        f.write('      route {0} next-hop {1};\n'.format(path, local_address))
                    f.write('''   }
}
''')

                startup.append('''env exabgp.log.destination={0}/{1}.log \
    exabgp.daemon.daemonize=true \
    exabgp.daemon.user=root \
    exabgp {0}/{1}.conf'''.format(self.guest_dir, p['router-id']))

        for p in peers:
            startup.append('ip a add {0} dev eth1'.format(p['local-address']))

        filename = '{0}/start.sh'.format(self.host_dir)
        with open(filename, 'w') as f:
            f.write('\n'.join(startup))
        os.chmod(filename, 0777)

        if 'config_only' in conf and conf['config_only']:
            return

        i = dckr.exec_create(container=self.name, cmd='{0}/start.sh'.format(self.guest_dir))
        cnt = 0
        for lines in dckr.exec_start(i['Id'], stream=True):
                for line in lines.strip().split('\n'):
                    cnt += 1
                    if cnt % 2 == 1:
                        if cnt > 1:
                            rm_line()
                        print 'tester booting.. ({0}/{1})'.format(cnt/2 + 1, len(conf['tester']))
