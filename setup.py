#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from distutils.core import setup

setup(
    name='xivo-dxtora',
    version='0.1',
    description='XIVO dxtora daemon',
    maintainer='Avencall',
    maintainer_email='xivo-users@lists.proformatique.com',
    url='http://www.xivo.io/',
    license='GPLv3',
    scripts=['bin/xivo-dxtora'],
    data_files=[('/etc/xivo-dxtora', ['etc/xivo-dxtora/config.conf'])],
)
