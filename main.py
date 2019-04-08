# -*- coding: utf-8 -*-
"AT Shell (not for importing!)"
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys

import colorama

from atshell import ShellBase

# pylint: disable=too-many-instance-attributes


class ATShell(ShellBase):
    """AT Shell is minimalistic shell
which implements some basic UNIX commands."""
    intro = "Welcome to AT Shell!\nType 'help' or '?' to list commands."
    prompt = "$ "

    cwd = Path.cwd()

    # pylint: disable=too-many-arguments
    def __init__(self, stdin=sys.stdin, stdout=sys.stdout,
                 stderr=sys.stderr, colored=True,
                 dyn_commands_dir="bin"):
        super().__init__(stdin, stdout, stderr, colored,
                         dyn_commands_dir)
        self.change_cwd(Path.cwd())

    def change_cwd(self, path):
        "Change current working directory (CWD)"
        self.cwd = path
        self.prompt = (colorama.Fore.BLUE + str(path)
                       + colorama.Fore.RESET + "$ ")

    def process_path(self, arg):
        """Convert relative path to absolute
(Please do 'shlex.split' before processing!)"""
        return self.cwd.joinpath(arg).resolve()

    # pylint: disable=unused-argument,invalid-name
    @staticmethod
    def do_EOF(arg):
        "Exit from shell"
        return True

    # pylint: disable=unused-argument
    @staticmethod
    def do_exit(arg):
        "Exit from shell"
        return True

    def do_cd(self, arg):
        """Usage: cd <DIR>
Change current directory to DIR (relative paths are supported)"""
        arg = shlex.split(arg)
        if len(arg) != 1:
            self.stderr.write("Error: expected 1 argument, found {0}\n"
                              .format(len(arg)))
            return
        arg = self.process_path(arg[0])

        if not arg.exists():
            self.stderr.write("Error: no such file or directory\n")
            return
        if not arg.is_dir():
            self.stderr.write("Error: not a directory\n")
            return
        self.change_cwd(arg)

    def do_cp(self, arg):
        """Usage: cp <SRC> <DST>
Copy file SRC to path DST (file or directory)."""
        arg = shlex.split(arg)
        if len(arg) != 2:
            self.stderr.write("Error: expected 2 arguments, found {0}\n"
                              .format(len(arg)))
            return
        src, dst = map(self.process_path, arg)

        if not src.exists():
            self.stderr.write("Error: no such file or directory\n")
            return
        if not src.is_file():
            self.stderr.write("Error: SRC is not a file\n")
            return
        shutil.copy2(str(src), str(dst))

    def do_echo(self, arg):
        "Print remaining part of line."
        self.stdout.write(arg + '\n')

    def do_ls(self, arg):
        """Usage: ls [DIR]
Show contents of DIR (default is current directory)"""
        arg = shlex.split(arg)
        if len(arg) > 1:
            self.stderr.write("Error: expected 0 or 1 argument, found {0}\n"
                              .format(len(arg)))
            return
        if not arg:
            arg = self.cwd
        else:
            arg = self.process_path(arg[0])

        if not arg.exists():
            self.stderr.write("Error: no such file or directory\n")
            return
        for elem in arg.iterdir():
            elem_mode = os.stat(str(elem)).st_mode
            if stat.S_ISDIR(elem_mode):
                self.stdout.write(colorama.Fore.BLUE)
            elif stat.S_ISLNK(elem_mode):
                self.stdout.write(colorama.Fore.CYAN)
            elif 'x' in stat.filemode(elem_mode):
                self.stdout.write(colorama.Fore.GREEN)
            else:
                self.stdout.write(colorama.Fore.RESET)
            self.stdout.write(elem.name + '\n')
        self.stdout.write(colorama.Fore.RESET)

    def do_mkdir(self, arg):
        """Usage: mkdir <DIR>
Create directory DIR (if it does not exist)."""
        arg = shlex.split(arg)
        if len(arg) != 1:
            self.stderr.write("Error: expected 1 argument, found {0}\n"
                              .format(len(arg)))
            return
        arg = self.process_path(arg[0])

        if arg.exists():
            self.stderr.write("Error: file or directory exists\n")
            return
        arg.mkdir()

    def do_mv(self, arg):
        """Usage: mv <SRC> <DST>
Move file SRC to path DST (file or directory)."""
        arg = shlex.split(arg)
        if len(arg) != 2:
            self.stderr.write("Error: expected 2 arguments, found {0}\n"
                              .format(len(arg)))
            return
        src, dst = map(self.process_path, arg)

        if not src.exists():
            self.stderr.write("Error: no such file or directory\n")
            return
        if not src.is_file():
            self.stderr.write("Error: SRC is not a file\n")
            return
        shutil.move(str(src), str(dst))

    def do_pwd(self, arg):
        "Print path to the current directory"
        self.stdout.write(str(self.cwd) + '\n')

    def do_rm(self, arg):
        """Usage: rm <FILE>
Remove file FILE."""
        arg = shlex.split(arg)
        if len(arg) != 1:
            self.stderr.write("Error: expected 1 argument, found {0}\n"
                              .format(len(arg)))
            return
        arg = self.process_path(arg[0])

        if not arg.exists():
            self.stderr.write("Error: no such file or directory\n")
            return
        if not arg.is_file():
            self.stderr.write("Error: not a file\n")
            return
        arg.unlink()

    def do_rmdir(self, arg):
        """Usage: rmdir <DIR>
Remove directory DIR (if it is empty)."""
        arg = shlex.split(arg)
        if len(arg) != 1:
            self.stderr.write("Error: expected 1 argument, found {0}\n"
                              .format(len(arg)))
            return
        arg = self.process_path(arg[0])

        if not arg.exists():
            self.stderr.write("Error: no such file or directory\n")
            return
        if not arg.is_dir():
            self.stderr.write("Error: not a directory\n")
            return
        with os.scandir(arg) as it:
            # pylint: disable=unused-variable
            for entry in it:
                self.stderr.write("Error: directory is not empty\n")
                return
        arg.rmdir()

    def do_run(self, arg):
        """Usage: run <STR>
Run external executable with arguments.
(Just like running STR in external shell.)"""
        if not arg:
            self.stderr.write("Error: expected something after 'run'\n")
            return
        try:
            # TODO: Fix encoding
            # (I think I need to use StreamRecoder.)

            # I could use subprocess.run, but it is badly compatible
            # with stream wrappers (AFAIK)
            obj = subprocess.Popen(shlex.split(arg),
                                   stdin=self.stdin,
                                   stdout=self.stdout,
                                   stderr=self.stderr)
            retcode = obj.wait()
            if retcode != 0:
                self.stderr.write(
                    "Error: command '{0}' returned non-zero exit status {1}\n"
                    .format(arg, retcode))
                return
        except FileNotFoundError:
            self.stderr.write("Error: file not found\n")


# with open("error.log", "w", encoding="utf-8") as file:
#     SHELL = ATShell(stdout=file)
#     SHELL.cmdloop()

#SHELL = ATShell(dyn_commands_dir="sbin.test")

SHELL = ATShell()
SHELL.cmdloop()
