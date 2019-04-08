"""Usage: touch <FILE>
Create new empty file FILE, if absent."""
import pathlib
import shlex


def execute(args_line, shell, stdin, stdout, stderr):
    # pylint: disable=missing-docstring,unused-argument
    arg = shlex.split(args_line)
    if len(arg) != 1:
        stderr.write("Error: expected 1 argument, found {0}\n"
                     .format(len(arg)))
        return
    arg = shell.process_path(arg[0])
    pathlib.Path(arg).touch()
