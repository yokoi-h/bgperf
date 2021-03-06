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

class ExaBGP(Container):
    def __init__(self, name, host_dir, guest_dir='/root/config', image='bgperf/exabgp'):
        super(ExaBGP, self).__init__(name, image, host_dir, guest_dir)

    @classmethod
    def build_image(cls, force=False, tag='bgperf/exabgp', checkout='HEAD', nocache=False):
        cls.dockerfile = '''
FROM ubuntu:latest
WORKDIR /root
RUN apt-get update && apt-get install -qy git python python-setuptools gcc python-dev
RUN easy_install pip
RUN git clone https://github.com/Exa-Networks/exabgp && \
(cd exabgp && git checkout {0} && pip install -r requirements.txt && python setup.py install)
RUN ln -s /root/exabgp /exabgp
'''.format(checkout)
        super(ExaBGP, cls).build_image(force, tag, nocache)

    def run(self, brname=''):
        return super(ExaBGP, self).run(brname)
