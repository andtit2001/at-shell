"""Usage: yes [ARG]
Constantly print the ARG (default is 'y') and newline character."""


def execute(args_line, shell, stdin, stdout, stderr):
    # pylint: disable=missing-docstring,unused-argument
    if not args_line:
        args_line = 'y'
    while True:
        stdout.write(args_line + '\n')
