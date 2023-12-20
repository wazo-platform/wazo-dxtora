# Copyright 2010-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Small daemon program that is used to push DHCP information to a
provisioning server.

DHCP information is passed to it by the dxtorc application.

"""

import errno
import logging
import optparse
import os
import signal
import socket
import sys

from wazo_auth_client import Client as AuthClient
from wazo_provd_client import Client as ProvdClient
from wazo_provd_client.exceptions import ProvdError
from xivo.chain_map import ChainMap
from xivo.config_helper import parse_config_file, read_config_file_hierarchy
from xivo.token_renewer import TokenRenewer
from xivo.user_rights import change_user
from xivo.xivo_logging import setup_logging

logger = logging.getLogger('wazo-dxtora')


DEFAULT_CONFIG = {
    'debug': False,
    'config_file': '/etc/wazo-dxtora/config.yml',
    'extra_config_files': '/etc/wazo-dxtora/conf.d/',
    'log_filename': '/var/log/wazo-dxtora.log',
    'pid_filename': '/run/wazo-dxtora/wazo-dxtora.pid',
    'unix_server_addr': '/run/wazo-dxtora/wazo-dxtora.ctl',
    'user': 'wazo-dxtora',
    'prov_server': {
        'host': 'localhost',
        'port': 8666,
        'prefix': None,
        'https': False,
    },
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'prefix': None,
        'https': False,
        'key_file': '/var/lib/wazo-auth-keys/wazo-dxtora-key.yml',
    },
}


class DHCPInfoSourceError(Exception):
    """Raised if there's an error while pulling DHCP information."""

    pass


class DHCPInfoSinkError(Exception):
    """Raised if there's an error while pushing DHCP information."""

    pass


class PidFileError(Exception):
    pass


class StreamDHCPInfoSink:
    """A destination for DHCP information objects.

    Write the DHCP information as a string to a file object.

    Useful for testing/debugging...

    """

    def __init__(self, fobj):
        self._fobj = fobj

    def close(self):
        pass

    def push(self, dhcp_info):
        self._fobj.write(str(dhcp_info) + '\n')


class ProvServerDHCPInfoSink:
    """A destination for DHCP information objects.

    Send the DHCP information to a provisioning server via its REST API.

    """

    def __init__(self, provd_client):
        self._provd_client = provd_client

    def close(self):
        pass

    def _do_push(self, dhcp_info):
        self._provd_client.devices.create_from_dhcp(dhcp_info)

    def push(self, dhcp_info):
        logger.info('Pushing DHCP info to prov server')
        try:
            self._do_push(dhcp_info)
        except ProvdError:
            raise
        except Exception as e:
            # XXX we are wrapping a bit too much
            raise DHCPInfoSinkError(e)


class UnixSocketDHCPInfoSource:
    """A source of DHCP information objects.

    Use a Unix datagram socket to get DHCP information.

    """

    def __init__(self, ctl_file, remove_file=False):
        """Create a new source.

        Raise a socket.error exception if the socket can't be binded to
        ctl_file.

        """
        if remove_file:
            try:
                os.remove(ctl_file)
            except OSError:
                pass
        self._ctl_file = ctl_file
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            self._sock.bind(ctl_file)
        except OSError:
            self._sock.close()
            raise

    def close(self):
        self._sock.close()
        _remove(self._ctl_file)

    def _check_op(self, op):
        # check that op is one of the 3 valid values
        if op not in ('commit', 'expiry', 'release'):
            raise DHCPInfoSourceError("invalid 'op' value: %s" % op)

    def _check_ip(self, ip):
        # check that ip is a dotted quad ip
        try:
            # Note that inet_aton accept strings with less than three dots.
            socket.inet_aton(ip)
        except OSError:
            raise DHCPInfoSourceError("invalid 'ip' value: %s" % ip)

    def _check_mac(self, mac):
        # check that mac is a lowercase, colon separated mac
        # TODO if we really care
        pass

    def _check_options(self, options):
        # check that options is a sequence of valid option
        for option in options:
            if len(option) < 3:
                raise DHCPInfoSourceError("invalid 'option' value: too short")
            try:
                num = int(option[:3], 10)
            except ValueError:
                raise DHCPInfoSourceError("invalid 'option' value: not int")
            else:
                if not 0 <= num <= 255:
                    raise DHCPInfoSourceError("invalid 'option' value: invalid code")

    def _decode(self, data):
        """Takes the raw data from a request and return an dhcp_info
        dict ('op', 'ip', 'mac' and 'options').

        """
        lines = list(filter(None, data.decode('utf-8').split('\n')))
        dhcp_info = {}

        def check_and_add(key, value):
            check_fun = getattr(self, '_check_' + key)
            check_fun(value)
            dhcp_info[key] = value

        try:
            check_and_add('op', lines[0])
            check_and_add('ip', lines[1])
            if dhcp_info['op'] == 'commit':
                check_and_add('mac', lines[2])
                check_and_add('options', lines[3:])
        except IndexError as e:
            raise DHCPInfoSourceError(e)
        else:
            return dhcp_info

    def pull(self):
        """Get a dhcp_info object from the source.

        Note: this is a blocking call.

        """
        logger.info('Pulling DHCP info from unix socket')
        data = self._sock.recvfrom(2048)[0]
        dhcp_info = self._decode(data)
        return dhcp_info


class Agent:
    """An agent that reads DHCP info from a source and send it to a sink in
    a loop.

    """

    def __init__(self, source, sink):
        """Create an agent."""
        self._source = source
        self._sink = sink

    def run(self):
        """Run the agent in loop."""
        while True:
            try:
                dhcp_info = self._source.pull()
                logger.info("Pulled DHCP info: (%(op)s, %(ip)s)", dhcp_info)
                logger.debug('DHCP info: %s', dhcp_info)
                self._sink.push(dhcp_info)
            except DHCPInfoSourceError as e:
                logger.error('Error while pulling info from source: %s', e)
            except DHCPInfoSinkError as e:
                logger.error('Error while pushing info to sink: %s', e)
            except Exception:
                logger.exception('Unspecified exception')


class PidFile:
    def _remove_stale_pid_file(self):
        try:
            fobj = open(self._pid_file)
        except OSError as e:
            if e.errno == errno.ENOENT:
                # pidfile doesn't exist -- do nothing
                pass
            else:
                raise
        else:
            try:
                pid = int(fobj.read().strip())
            finally:
                fobj.close()
            # check if a process with the given pid exist by sending a signal
            # with value 0 (see "man 2 kill" for more info).
            try:
                os.kill(pid, 0)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    # no such process -- remove stale pidfile
                    logger.info('Found stale pidfile %s, removing it', self._pid_file)
                    os.remove(self._pid_file)
                else:
                    raise
            else:
                logger.error('Found fresh pidfile %s', self._pid_file)

    def _create_pid_file(self):
        pid = os.getpid()
        tmp_pid_file = self._pid_file + '.' + str(pid)
        try:
            fpid = open(tmp_pid_file, 'w')
        except OSError as e:
            raise PidFileError("couldn't create tmp pid file: %s" % e)
        else:
            try:
                fpid.write("%s\n" % pid)
            finally:
                fpid.close()
            try:
                os.link(tmp_pid_file, self._pid_file)
            except OSError as e:
                raise PidFileError("couldn't create pid file: %s" % e)
            finally:
                os.unlink(tmp_pid_file)

    def __init__(self, pid_file):
        self._pid_file = pid_file
        self._remove_stale_pid_file()
        self._create_pid_file()

    def _remove_pid_file(self):
        _remove(self._pid_file)

    def close(self):
        self._remove_pid_file()


def _read_config_from_commandline():
    parser = optparse.OptionParser()
    opt, args = parser.parse_args()

    result = {'prov_server': {}, 'auth': {}}
    if len(args) >= 1:
        result['prov_server']['host'] = args[0]
    return result


def _read_config():
    cli_config = _read_config_from_commandline()
    file_config = read_config_file_hierarchy(ChainMap(cli_config, DEFAULT_CONFIG))
    service_key = _load_key_file(ChainMap(cli_config, file_config, DEFAULT_CONFIG))
    return ChainMap(cli_config, service_key, file_config, DEFAULT_CONFIG)


def _load_key_file(config):
    key_file = parse_config_file(config['auth']['key_file'])
    return {
        'auth': {
            'username': key_file.get('service_id'),
            'password': key_file.get('service_key'),
        }
    }


def _remove(file):
    # remove the file if present in a way that doesn't modify the stack
    # trace and doesn't raise an exception
    try:
        pass
    finally:
        try:
            os.remove(file)
        except OSError:
            pass


def _sig_handler(signum, frame):
    logger.info('Received signal, exiting.')
    raise SystemExit()


def main():
    config = _read_config()

    setup_logging(config['log_filename'], debug=config['debug'])

    if 'host' not in config['prov_server']:
        logger.error('error: no provd host specified. Exiting.')
        sys.exit(1)

    user = config['user']
    if user:
        change_user(user)

    auth_client = AuthClient(**config['auth'])
    provd_client = ProvdClient(**config['prov_server'])
    token_renewer = TokenRenewer(auth_client)
    token_renewer.subscribe_to_token_change(provd_client.set_token)
    sink = ProvServerDHCPInfoSink(provd_client)

    with token_renewer:
        try:
            pidfile = PidFile(config['pid_filename'])
            try:
                source = UnixSocketDHCPInfoSource(config['unix_server_addr'], True)
                try:
                    signum = signal.SIGTERM
                    old_handler = signal.signal(signum, _sig_handler)
                    try:
                        agent = Agent(source, sink)
                        agent.run()
                    finally:
                        signal.signal(signum, old_handler)
                finally:
                    source.close()
            finally:
                pidfile.close()
        finally:
            sink.close()
