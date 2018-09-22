""" a base class that implements command execution much like python's std library cmd module.
Unlike that module, this is simpler and works by executing strings, not reading from stdin.
This makes it easy to use when not implementing a commandline interface, such as this programs
tkinter gui
"""

import contextlib
import io
import traceback
import inspect
import string


class IncorrectArgsError(Exception):

    def __init__(self, cmd, n_expected_args, n_passed_args, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cmd = cmd
        self.n_expected_args = n_expected_args
        self.n_passed_args = n_passed_args


class Console:

    def __init__(self, intro=None):
        self._output = io.StringIO()

        if intro is not None:
            self._output.write(intro)

        self._create_default_helpers()

    @property
    def output(self):
        return self._output.getvalue()

    @staticmethod
    def _fallback_cmd():
        print(f'Invalid command. Use ? or "help" to see all valid commands.')

    def _create_default_helpers(self):
        """ finds all self.do_{cmd} methods and assigns a default self.help_{cmd}
         if not already present. (default help_cmd is print(inspect.getdoc(self.do_{cmd})) )
        """
        do_methods = {m[len('do_'):] for m in dir(self) if callable(getattr(self, m))
                      and m.startswith('do_')}
        help_methods = {m[len('help_'):] for m in dir(self) if callable(getattr(self, m))
                        and m.startswith('help_')}

        missing_helpers = do_methods - help_methods

        for m in missing_helpers:
            setattr(self, f'help_{m}', lambda: print(inspect.getdoc(getattr(self, f'do_{m}'))))

    @staticmethod
    def validate_string(string_):
        valid_chars = string.ascii_letters + string.digits + ' '
        # string.split(sep=' ') will have empty strings in it if
        # there were more than 1 consecutive spaces in any place
        return all(char in valid_chars for char in string_) and all(string_.spit(sep=' '))

    def exec_cmd(self, str_cmd, default=None):
        """ method will try and call self.do_{str_cmd} method. If it fails,
        an optional default method will be called. If default is None, it will call
        self._fallback_cmd.
        """
        # remove all double spaces, and all other whitespace in the command string
        str_cmd = " ".join(str_cmd.split())

        cmd = str_cmd.split(sep=' ')[0].lower()
        # anything after the first space are arguments
        args = str_cmd.split(sep=' ')[1:]

        # redirect stdout to self.output
        with contextlib.redirect_stdout(self._output):
            try:
                # if help is on its own
                if cmd in ('?', 'help') and not args:
                    self.do_help()

                # if it has args, then call self.help_{arg[0]}
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
                    self._fallback_cmd()

            except IncorrectArgsError as ex:
                print(f'Error: {ex.cmd} command expects {ex.n_expected_args} arg(s) but received {ex.n_passed_args}')

            # print any other unhandled exception to output
            except Exception:
                print(traceback.format_exc())

    def do_help(self):
        """ Displays all possible commands. """
        print('Possible Commands:\n')
        print('\n'.join([d[len('do_'):] for d in dir(self) if callable(getattr(self, d)) and d.startswith('do_')]))


if __name__ == '__main__':
    c = Console()
    c.exec_cmd('help ')

    print(c._output.getvalue())
