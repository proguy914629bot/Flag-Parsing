import argparse
import inspect
import functools

from collections import namedtuple
from discord.utils import escape_mentions
from discord.ext import commands

ParserResult = namedtuple("ParserResult", "result action arg_string")


class ArgumentParsingError(commands.CommandError):
    def __init__(self, message):
        super().__init__(escape_mentions(message))


class DontExitArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.ctx = None
        kwargs.pop('add_help', False)
        super().__init__(*args, add_help=False, **kwargs)

    def error(self, message):
        raise ArgumentParsingError(message)

    def _get_value(self, action, arg_string):
        type_func = self._registry_get('type', action.type, action.type)
        param = [arg_string]

        if hasattr(type_func, '__module__') and type_func.__module__ is not None:
            module = type_func.__module__
            if module.startswith('discord') and not module.endswith('converter'):
                # gets the default discord.py converter
                try:
                    type_func = getattr(commands.converter, type_func.__name__ + 'Converter')
                except AttributeError:
                    pass

        # for custom converter compatibility
        if inspect.isclass(type_func):
            if issubclass(type_func, commands.Converter):
                type_func = type_func().convert
                param.insert(0, self.ctx)

        if not callable(type_func):
            msg = '%r is not callable'
            raise argparse.ArgumentError(action, msg % type_func)

        # if type is bool, use the discord.py's bool converter
        if type_func is bool:
            type_func = commands.core._convert_to_bool

        # convert into a partial function
        result = functools.partial(type_func, *param)
        # return the function, with it's action and arg_string in a namedtuple.
        return ParserResult(result, action, arg_string)

    # noinspection PyMethodOverriding
    def parse_args(self, args, namespace=None, *, ctx):
        self.ctx = ctx
        return super().parse_args(args, namespace)
