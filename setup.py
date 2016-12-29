#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from distutils.core import setup

setup(
    name='xivo-dxtora',
    version='0.1',
    description='XIVO dxtora daemon',
    author='Wazo Authors',
    author_email='dev.wazo@gmail.com',
    url='http://wazo.community',
    license='GPLv3',
    scripts=['bin/xivo-dxtora'],
    data_files=[('/etc/xivo-dxtora', ['etc/xivo-dxtora/config.conf'])],
)
