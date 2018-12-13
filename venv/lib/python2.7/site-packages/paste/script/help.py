from __future__ import print_function
# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
from .command import Command, get_commands
from .command import parser as base_parser

class HelpCommand(Command):

    summary = "Display help"
    usage = '[COMMAND]'

    max_args = 1

    parser = Command.standard_parser()

    def command(self):
        if not self.args:
            self.generic_help()
            return

        name = self.args[0]
        commands = get_commands()
        if name not in commands:
            print('No such command: %s' % name)
            self.generic_help()
            return

        command = commands[name].load()
        runner = command(name)
        runner.run(['-h'])

    def generic_help(self):
        base_parser.print_help()
        print()
        commands_grouped = {}
        commands = get_commands()
        longest = max([len(n) for n in commands.keys()])
        for name, command in commands.items():
            try:
                command = command.load()
            except Exception as e:
                print('Cannot load command %s: %s' % (name, e))
                continue
            if getattr(command, 'hidden', False):
                continue
            commands_grouped.setdefault(
                command.group_name, []).append((name, command))
        commands_grouped = commands_grouped.items()
        commands_grouped = sorted(commands_grouped)
        print('Commands:')
        for group, commands in commands_grouped:
            if group:
                print(group + ':')
            commands.sort()
            for name, command in commands:
                print('  %s  %s' % (self.pad(name, length=longest),
                                    command.summary))
                #if command.description:
                #    print self.indent_block(command.description, 4)
            print()

