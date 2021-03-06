#!/usr/bin/env python3
# -*- coding: utf8 -*-

from io import open
import argparse
import sys
import os
import yaml

class Conf(dict):
    """
        Configuration dictionnary.

        It use yaml configuration file by default, and some option can be
        change by passing it in argument (with argparse)
    """

    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    _fallback_conf = os.path.join(__location__, "_fallback_conf/conf.yml.orig")

    parser = argparse.ArgumentParser(
        description='Stepmania configuration',
        conflict_handler='resolve'
    )

    parser.add_argument('-name', '--server.name',
                        dest='server.name',
                        help="Server's name",
                        default="Stepmania")

    parser.add_argument('-motd', '--server.motd',
                        dest='server.motd',
                        help="Server's description",
                        default="Welcome to this stepmania server")

    parser.add_argument('-ip', '--server.ip',
                        dest='server.ip',
                        help="IP to listen to (default: 0.0.0.0)",
                        default="0.0.0.0")

    parser.add_argument('-port', '--server.port',
                        dest='server.port',
                        type=int,
                        help="Port to listen to (default: 8765)",
                        default=8765)

    parser.add_argument('-users', '--server.max_users',
                        dest='server.max_users',
                        type=int,
                        help="Maximum number of users allow (-1 = infinite) (default: -1)",
                        default=-1)

    parser.add_argument('--auth.plugin',
                        dest='auth.plugin',
                        type=str,
                        help="Plugin to use for auth (default: database)",
                        default='database')

    parser.add_argument('--disable_user_creation',
                        dest='auth.autocreate',
                        action='store_false',
                        help="Don't allow user creation on login")

    parser.add_argument('--update_schema',
                        dest='database.update_schema',
                        action='store_true',
                        help="Drop all the db tables and recreate them")

    def __init__(self, *args):
        self._raw_args = args

        self.parser.add_argument(
            '-c', '--config',
            dest='config',
            help="Server's configuration file (default: %s)" % self._default_conf(),
            default=self._default_conf()
        )

        dict.__init__(self)
        self._args = self.parser.parse_args(args)
        default_arg = self.parser.parse_args([])

        self.configuration_file = self._find_configuration_file(self._args.config)

        with open(self.configuration_file, 'r', encoding='utf-8') as stream:
            self.update(yaml.load(stream), allow_unicode=True)

        for key, value in vars(self._args).items():
            self.add_to_conf(self, key, value, getattr(default_arg, key, None) != value)

        self.server = self["server"]
        self.database = self.get("database", {})
        self.auth = self["auth"]
        self.logger = self.get("logger", {})
        self.score = self.get("score", {})
        self.plugins = self.get("plugins")
        if not self.plugins:
            self.plugins = {}

        self.additional_servers = self.get("additional_servers")
        if not self.additional_servers:
            self.additional_servers = []

    def reload(self):
        """ Reload the configuration file """

        self.__init__(*self._raw_args)

    @staticmethod
    def add_to_conf(conf, arg, value, replace=True):
        """
            Add the given value to the conf

            :param dict conf: The configuration dictionnary
            :param str arg: The path of the key, with dot notation
            :param value: Value to assign
            :param bool replace: If the key already exist replace it

            :Example:

            >>> conf = {}
            >>> Conf.add_to_conf(conf, "root.key", "value")
            >>> print(conf)
            {'root': {'key': 'value'}}

            >>> Conf.add_to_conf(conf, "root.key", "new_value", replace=False)
            >>> print(conf)
            {'root': {'key': 'value'}}

            >>> Conf.add_to_conf(conf, "root.key", "new_value", replace=True)
            >>> print(conf)
            {'root': {'key': 'new_value'}}
        """

        arg = arg.split(".")
        arg.reverse()
        while True:
            option = arg.pop()
            if not arg:
                if replace or option not in conf:
                    conf[option] = value
                return

            if option not in conf:
                conf[option] = {}

            conf = conf[option]

    @classmethod
    def _find_configuration_file(cls, path):
        if os.path.isfile(path):
            return path

        if os.path.isfile(path + ".orig"):
            return path + ".orig"

        return cls._fallback_conf

    @staticmethod
    def _in_py2exe():
        return hasattr(sys, "frozen")

    @classmethod
    def _default_conf(cls):
        if os.path.splitdrive(sys.executable)[0] == "":
            return "/etc/smserver/conf.yml"

        if cls._in_py2exe():
            return os.path.join(
                os.path.dirname(sys.executable),
                "conf/conf.yml"
                )

        return "conf.yml"

if __name__ == "__main__":
    import doctest
    doctest.testmod()
