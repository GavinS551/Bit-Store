""" a base class that implements command execution much like python's std library cmd module.
Unlike that module, this is simpler and works by executing strings, not reading from stdin.
This makes it easy to use when not implementing a commandline interface, such as this programs
tkinter gui
"""

import contextlib
import io
import traceback
import inspect


class IncorrectArgsError(Exception):

    def __init__(self, cmd, n_expected_args, n_passed_args, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cmd = cmd
        self.n_expected_args = n_expected_args
        self.n_passed_args = n_passed_args


class Console:
    """
    This class should be sub-classed. You defined methods called do_{something},
    and when the string "{something}" is passed into exec_cmd, the method do_{something}
    will be called. Default help commands will be created for do_ methods, which just displays
    the method's docstring, which is usually enough. More complicated help commands can be
    created by defining a help_{something} method that will be called instead. The default do_help
    will list all possible do_ commands.
    """

    def __init__(self, intro=None):
        self._output = io.StringIO()

        if intro is not None:
            self._output.write(intro)

        self.command_history = []

        self._create_default_helpers()

    @property
    def output(self):
        return self._output.getvalue()

    def clear_output(self):
        self._output = io.StringIO()

    @staticmethod
    def fallback_cmd():
        print(f'Invalid command. Type ? or "help" to see all valid commands.')

    def _create_default_helpers(self):
        """ finds all self.do_{cmd} methods and assigns a default self.help_{cmd}
         if not already present. (default help_cmd is print(inspect.getdoc(self.do_{cmd})) )
        """

        make_helper = lambda method: lambda: print(inspect.getdoc(getattr(self, f'do_{method}')))

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
        # remove all double spaces, and all other whitespace in the command string
        str_cmd = " ".join(str_cmd.split())

        cmd = str_cmd.split(sep=' ')[0].lower()
        # anything after the first space are arguments
        args = str_cmd.split(sep=' ')[1:]

        self.command_history.append(cmd)

        # redirect stdout to self.output
        with contextlib.redirect_stdout(self._output):
            try:
                if print_cmd:
                    print(cmd, *args)

                # if help is on its own
                if cmd in ('?', 'help') and not args:
                    self.do_help()

                # if it has args, then pass into do_help
                elif cmd in ('?', 'help') and args:
                    if len(args) > 1:
                        raise IncorrectArgsError('help', 1, len(args))
                    getattr(self, f'help_{args[0]}')()

                else:
                    getattr(self, f'do_{cmd}')(*args)

            except AttributeError:
                if default is not None:
                    default()
                else:
                    self.fallback_cmd()

            except IncorrectArgsError as ex:
                print(f'Error: {ex.cmd} command expects {ex.n_expected_args} arg(s) but received {ex.n_passed_args}')

            # print any other unhandled exception to output
            except Exception:
                print(traceback.format_exc())

    # if a cmd_name is passed in, a specific self.help_function will be called
    def do_help(self):
        """ Displays all possible commands. """
        print('Possible Commands:')
        print('(Use "help <command>" for specific information)\n')
        print('\n'.join([d[len('do_'):] for d in dir(self) if callable(getattr(self, d)) and d.startswith('do_')]))
