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


class IncorrectArgsError(Exception):
    """ when raised in a 'do' method in the console class, the below wrapper will
    automatically show the user the required args and their type annotations (if present)
    in the exception string.
    """
    pass


class ConsoleArgErrorsMeta(type):

    def __new__(mcs, name, bases, attrs):

        for name_, value in attrs.items():
            if isinstance(value, types.FunctionType) and name_.startswith('do_'):
                attrs[name_] = mcs._args_error_info_decorate(value)

        mcs.created_cls = super().__new__(mcs, name, bases, attrs)
        return mcs.created_cls

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
                    cls = mcs.created_cls
                    # check if a self or cls arg should be ignored
                    if isinstance(cls.__dict__[func.__name__], classmethod) or \
                       not isinstance(cls.__dict__[func.__name__], staticmethod):
                        impl_arg_num = 1
                    else:
                        impl_arg_num = 0

                    if len(sig.parameters) - impl_arg_num != len(args) - impl_arg_num + len(kwargs):
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

                err_str = f'Error: "{cmd_name}" expects {num_args} argument(s)'
                if num_args > 0:
                    err_str += f': {str_arg_annos}'

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

    TODO: add info about IncorrectArgsError Handling
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

        make_helper = lambda method: lambda: print(f"'{method}': {inspect.getdoc(getattr(self, f'do_{method}'))}")

        do_methods = {m[len('do_'):] for m in dir(self) if callable(getattr(self, m))
                      and m.startswith('do_')}
        help_methods = {m[len('help_'):] for m in dir(self) if callable(getattr(self, m))
                        and m.startswith('help_')}

        missing_helpers = do_methods - help_methods

        for m in missing_helpers:
            setattr(self, f'help_{m}', make_helper(m))

    def exec_cmd(self, str_cmd, default=None, print_cmd=True):
        """ method will try and call self.do_{str_cmd} method. If it fails,
        an optional default method will be called. If default is None, it will call
        self._fallback_cmd.
        """
        # redirect stdout to self.output
        with contextlib.redirect_stdout(self._output):

            # remove all double spaces, and all other whitespace in the command string
            str_cmd = " ".join(str_cmd.split())

            cmd = str_cmd.split(sep=' ')[0].lower()
            # anything after the first space are arguments
            _args = ' '.join(str_cmd.split(sep=' ')[1:])

            # print command so double quotes in args will persist
            if print_cmd:
                print(cmd, _args)
                print()

            args = []
            _last_chop_idx = 0
            _ignore_spaces = False
            for i, char in enumerate(_args):
                if char == '"' and not _ignore_spaces:
                    _ignore_spaces = True

                # second quote found
                elif char == '"' and _ignore_spaces:
                    args.append(_args[_last_chop_idx+1:i])
                    _last_chop_idx = i
                    _ignore_spaces = False

                elif char == ' ' and not _ignore_spaces:
                    args.append(_args[_last_chop_idx:i])
                    _last_chop_idx = i

                elif i == len(_args) - 1:
                    if _ignore_spaces:
                        print('Error: Closing quote not found!\n')
                        return
                    args.append(_args[_last_chop_idx:])

                self.command_history.append(cmd)

            try:
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
