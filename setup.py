#!/usr/bin/env python3
# Copyright 2010-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from setuptools import setup

setup(
    name='wazo-dxtora',
    version='0.2',
    description='Wazo dxtora daemon',
    author='Wazo Authors',
    author_email='dev@wazo.community',
    url='http://wazo.community',
    license='GPLv3',
    scripts=['bin/wazo-dxtora'],
)
