""" a base class that implements command execution much like python's std library cmd module.
Unlike that module, this is simpler and works by executing strings, not reading from stdin.
This makes it easy to use when not implementing a commandline interface, such as this programs
tkinter gui
"""

import contextlib
import io
import traceback
import inspect
import functools
import types
import csv


class IncorrectArgsError(Exception):
    """ when raised in a 'do' method in the console class, the below wrapper will
    automatically show the user the required args and their type annotations (if present)
    in the exception string.
    """
    pass


# TODO fix staticmethods and classmethods
class ConsoleArgErrorsMeta(type):

    def __new__(mcs, name, bases, attrs):

        for name_, value in attrs.items():
            if isinstance(value, types.FunctionType) and name_.startswith('do_'):
                attrs[name_] = mcs._args_error_info_decorate(value)

        return super().__new__(mcs, name, bases, attrs)

    @classmethod
    def _args_error_info_decorate(mcs, func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):

            try:
                func(*args, **kwargs)

            except (IncorrectArgsError, TypeError) as ex:

                sig = inspect.signature(func)

                # makes sure TypeError was raised from incorrect
                # args. If it was raised for any other reason it
                # will be re-raised
                if isinstance(ex, TypeError):

                    if len(sig.parameters) != len(args) + len(kwargs):
                        other_type_error = False
                    else:
                        other_type_error = True

                    if other_type_error:
                        raise ex

                cmd_name = func.__name__[len('do_'):]
                num_args = len(sig.parameters)

                if 'self' in sig.parameters:
                    num_args -= 1

                arg_annos = []
                for n, p in sig.parameters.items():
                    if p.annotation != sig.empty:
                        arg_annos.append((n, p.annotation.__name__))
                    else:
                        arg_annos.append((n, None))

                str_arg_annos = ''
                for i, (arg_name, anno) in enumerate(arg_annos, start=1):
                    # ignore self
                    if arg_name == 'self':
                        continue

                    if anno is not None:
                        str_arg_annos += f"'{arg_name}': {anno}"
                    else:
                        str_arg_annos += f"'{arg_name}'"

                    # concatenate the comma if it isn't the end of the list
                    if i < len(arg_annos):
                        str_arg_annos += ', '

                err_str = f'Error: "{cmd_name}" expects {num_args} argument(s) '
                if num_args > 0:
                    err_str += f'<arg: type>: {str_arg_annos}'

                raise IncorrectArgsError(err_str)

        return wrapper


class Console(metaclass=ConsoleArgErrorsMeta):
    """
    This class should be sub-classed. You defined methods called do_{something},
    and when the string "{something}" is passed into exec_cmd, the method do_{something}
    will be called. Default help commands will be created for do_ methods, which just displays
    the method's docstring, which is usually enough. More complicated help commands can be
    created by defining a help_{something} method that will be called instead. The default do_help
    will list all possible do_ commands.

    If incorrect amount of arguments are passed into a command, it will automatically
    be caught and a detailed error message containing expected args and type annotations
    (if present) will be displayed. If IncorrectArgsError is raised inside any do_ method,
    the above will also happen (no need to pass any params to Exception). This is helpful for
    type validation as the type annotations will be displayed in the error message.
    """

    def __init__(self, intro=None, stdout=None):
        # if stdout is None, it will default to a StringIO object.
        # All methods executed in self.exec_cmd will have stdout
        # redirected.
        # complete stdout value can be accessed through self.output property
        # that will not move file stream (uses getvalue() method)
        if stdout is None:
            self._output = io.StringIO()
        else:
            self._output = stdout

        if intro is not None:
            self._output.write(intro)

        self.command_history = []

        self._create_default_helpers()

    @property
    def output(self):
        return self._output.getvalue()

    def clear_output(self):
        self._output.seek(0)
        self._output.truncate()

    @staticmethod
    def fallback_cmd():
        print(f'Invalid command. Type ? or "help" to see all valid commands.')

    def _create_default_helpers(self):
        """ finds all self.do_{cmd} methods and assigns a default self.help_{cmd}
         if not already present. (default help_cmd is print(inspect.getdoc(self.do_{cmd})) )
        """

        make_helper = \
            lambda method: lambda: print(f"'{method}': "
                                         f"<args = "
                                         f"{list(inspect.signature(getattr(self, f'do_{method}')).parameters.keys())}> "
                                         f"{inspect.getdoc(getattr(self, f'do_{method}'))}")

        do_methods = {m[len('do_'):] for m in dir(self) if callable(getattr(self, m))
                      and m.startswith('do_')}
        help_methods = {m[len('help_'):] for m in dir(self) if callable(getattr(self, m))
                        and m.startswith('help_')}

        missing_helpers = do_methods - help_methods

        for m in missing_helpers:
            setattr(self, f'help_{m}', make_helper(m))

    @staticmethod
    def _parse_str_cmd(str_cmd):
        """ returns a tuple containing cmd name, and args (in list).
        (separated by spaces except when string is enclosed in double-quotes)
        """

        # remove all double spaces, and all other whitespace in the command string
        str_cmd = ' '.join(str_cmd.split())

        cmd = str_cmd.split()[0].lower()

        # anything after the first space are arguments
        _args = ' '.join(str_cmd.split()[1:])
        args = [a for a in csv.reader([_args], delimiter=' ')][0]

        return cmd, args

    def exec_cmd(self, str_cmd, default=None, print_cmd=True):
        """ method will try and call self.do_{str_cmd} method. If there is not defined do_
        method, an optional default method will be called. If default is None, it will call
        self._fallback_cmd.
        """
        # redirect stdout to self.output
        with contextlib.redirect_stdout(self._output):

            cmd, args = self._parse_str_cmd(str_cmd)

            # print command so double quotes in args will persist
            if print_cmd:
                print(str_cmd, '\n')

            self.command_history.append(str_cmd)

            try:
                # special case for question mark
                if cmd == '?':
                    cmd = 'help'
                cmd_attr = getattr(self, f'do_{cmd}')

            except AttributeError:
                if default is not None:
                    default()
                else:
                    self.fallback_cmd()

                return

            try:

                # if help is on its own
                if cmd in ('?', 'help') and not args:
                    self.do_help()

                # if it has args, then pass into do_help
                elif cmd in ('?', 'help') and args:
                    self.do_help(cmd=args[0])

                else:
                    cmd_attr(*args)

            except IncorrectArgsError as ex:
                print(str(ex))

            # print any other unhandled exception to output
            except Exception:
                print(traceback.format_exc())

    # if a cmd_name is passed in, a specific self.help_function will be called
    def do_help(self, cmd=None):
        """ Displays all possible commands. """
        if cmd is not None:
            getattr(self, f'help_{cmd}')()

        else:
            print('Possible Commands:')
            print('(Use "help <command>" for specific information)\n')
            print('\n'.join([d[len('do_'):] for d in dir(self) if callable(getattr(self, d)) and d.startswith('do_')]))
