# -*- coding: utf-8 -*-
"""
This module provides class ShellBase which can be used for
creating advanced shells.
"""
import cmd
# from codecs import getdecoder, getencoder, getreader, getwriter,\
# StreamRecoder
import importlib
# import locale
import shlex
import sys

import colorama

# pylint: disable=too-many-instance-attributes


class ShellBase(cmd.Cmd):
    """
    Base class that extends cmd.Cmd with:
    1) Colored output
        2) Separate handling of stdout and stderr
    3) Dynamic loading of commands from specified directory
    3.1) Path to the directory should be specified in "package-style"
    (It is used as 'package' parameter in importlib.import_module)
    3.2) If command exists but is not loaded, it will be loaded AUTOMATICALLY!
    4) CTRL-C handling
    """
    colored_output = False
    # Original streams (from __init__)
    orig_stdin, orig_stdout, orig_stderr = None, None, None
    # Wrapped stderr ('stdin' and 'stdout' are already defined in 'Cmd')
    stderr = None
    # Temporary variables for standard streams
    temp_stdin, temp_stdout, temp_stderr = None, None, None

    old_stderr_write = None

    # external_shell_encoding = None
    dyn_commands = dict()
    dyn_commands_dir = None

    # pylint: disable=too-many-arguments
    def __init__(self, stdin, stdout, stderr,
                 colored=False, dyn_commands_dir=None):
        cmd.Cmd.__init__(self, stdin=stdin, stdout=stdout)
        self.orig_stdin, self.orig_stdout, self.orig_stderr =\
            stdin, stdout, stderr
        self.dyn_commands_dir = dyn_commands_dir
        self.colored_output = colored
        # self.external_shell_encoding = locale.getdefaultlocale()[1]
        # self.external_shell_encoding = 'cp866'

    def preloop(self):
        self.temp_stdin, self.temp_stdout, self.temp_stderr =\
            sys.stdin, sys.stdout, sys.stderr
        sys.stdin, sys.stdout, sys.stderr =\
            self.orig_stdin, self.orig_stdout, self.orig_stderr

        if self.colored_output:
            colorama.init()
        else:
            colorama.init(strip=True, convert=False)

        self.stdin, self.stdout, self.stderr =\
            sys.stdin, sys.stdout, sys.stderr
        sys.stdin, sys.stdout, sys.stderr =\
            self.temp_stdin, self.temp_stdout, self.temp_stderr
        self.temp_stdin, self.temp_stdout, self.temp_stderr = None, None, None

        # This line fixes 'colorama' in input()...
        # and breaks 'readline'
        self.use_rawinput = 0
        # TODO: Fix 'readline' by... I don't even know how...
        if self.colored_output:
            self.old_stderr_write = self.stderr.write
            self.stderr.write = lambda obj:\
                self.old_stderr_write(colorama.Fore.RED
                                      + obj + colorama.Fore.RESET)

    def cmdloop(self, intro=None):
        self.stdout.write(self.intro + '\n')
        while True:
            try:
                super().cmdloop(intro="")
                break
            except KeyboardInterrupt:
                # TODO: Fix the "flush delay" (probably with 'raw_input')
                self.stdout.write("^C\n")

    def postloop(self):
        if self.colored_output:
            self.stderr.write = self.old_stderr_write
        self.stdin, self.stdout, self.stderr = None, None, None

    def precmd(self, line):
        if not line:
            return line
        cmd_name = self.parseline(line)[0]
        if not cmd_name:
            return line
        if cmd_name == "EOF":
            return "exit"

        try:
            getattr(self, "do_" + cmd_name)
        except AttributeError:
            try:
                self.do_load(cmd_name, True)
            except ImportError:
                # Error will be reported by 'self.default(line)'
                pass
        return line

    def default(self, line):
        cmd_name = self.parseline(line)[0]
        self.stderr.write("Error: command '{0}' not found\n".format(cmd_name))

    def get_names(self):
        # Small patch needed for "dynamically loaded commands"
        return dir(self)

    # pylint: disable=unused-argument
    @staticmethod
    def do_exit(arg):
        """Exit from shell"""
        return True

    def do_load(self, arg, called_from_precmd=False):
        # pylint: disable=missing-docstring
        if called_from_precmd:
            if self.dyn_commands_dir is None:
                raise ImportError
            mod = importlib.import_module('.' + arg, self.dyn_commands_dir)
            self.dyn_commands[arg] = mod
            setattr(self, "do_" + arg,
                    lambda args_line: mod.execute(args_line,
                                                  self,
                                                  self.stdin,
                                                  self.stdout,
                                                  self.stderr))
            setattr(getattr(self, "do_" + arg),
                    "__doc__", mod.__doc__)
            return

        arg = shlex.split(arg)
        if len(arg) != 1:
            self.stderr.write("Error: expected 1 argument, found {0}\n"
                              .format(len(arg)))
            return
        arg = arg[0]

        try:
            getattr(self, "do_" + arg)
            importlib.reload(self.dyn_commands[arg])
            setattr(getattr(self, "do_" + arg),
                    "__doc__", getattr(self.dyn_commands[arg], "__doc__", ''))
        except AttributeError:
            try:
                if self.dyn_commands_dir is None:
                    raise ImportError
                mod = importlib.import_module('.' + arg, self.dyn_commands_dir)
                self.dyn_commands[arg] = mod
                setattr(self, "do_" + arg,
                        lambda args_line: self.dyn_commands[arg]
                        .execute(args_line,
                                 self,
                                 self.stdin,
                                 self.stdout,
                                 self.stderr))
                setattr(getattr(self, "do_" + arg),
                        "__doc__", getattr(mod, "__doc__", ''))
            except ImportError:
                self.stderr.write("Error: command '{0}' not found\n"
                                  .format(arg))
        except ModuleNotFoundError:
            delattr(self, "do_" + arg)
            del self.dyn_commands[arg]
            self.stderr.write("Error: command '{0}' not found\n"
                              .format(arg))

    def do_unload(self, arg):
        """Usage: unload <ARG>
Try to unload command ARG."""
        arg = shlex.split(arg)
        if len(arg) != 1:
            self.stderr.write("Error: expected 1 argument, found {0}\n"
                              .format(len(arg)))
            return
        arg = arg[0]

        try:
            getattr(self, "do_" + arg)
        except AttributeError:
            self.stderr.write("Error: command '{0}' not found\n"
                              .format(arg))
            return
        # pylint: disable=superfluous-parens
        if ("do_" + arg) in dir(self.__class__):
            self.stderr.write("""Error: internal command '{0}' \
cannot be unloaded\n""".format(arg))
            return
        delattr(self, "do_" + arg)
        del self.dyn_commands[arg]

    def help_load(self):
        """
        Print help for 'load' command.
        """
        self.stdout.write("""Usage: load <ARG>
Try to (re)load command ARG from directory './{0}'.\n"""
                          .format(self.dyn_commands_dir.replace('.', '/')))
