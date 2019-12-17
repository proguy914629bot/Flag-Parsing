import shlex

import discord
from discord.ext import commands

from . import _parser

__all__ = ["add_flag", "command", "group", "FlagCommand", "FlagGroup"]


def command(**kwargs):
    def inner(func):
        if 'cls' not in kwargs:
            kwargs['cls'] = FlagCommand

        if not issubclass(kwargs['cls'], FlagCommand):
            raise TypeError("'cls' kwarg must inherit from FlagCommand")
        print("1")
        func.parser = _parser.DontExitArgumentParser()
        print(func.__globals__.keys())
        return commands.command(**kwargs)(func)
    return inner


def group(**kwargs):
    def inner(func):
        if 'cls' not in kwargs:
            kwargs['cls'] = FlagGroup

        if not issubclass(kwargs['cls'], FlagCommand):
            raise TypeError("'cls' kwarg must inherit from FlagGroup")
        print(2)
        func.parser = _parser.DontExitArgumentParser()
        print(func.__globals__.keys())
        return commands.group(**kwargs)(func)
    return inner


def add_flag(*flag_names, **kwargs):
    def inner(func):
        if isinstance(func, commands.Command):
            nfunc = func.callback
        else:
            nfunc = func
        print(3)
        if not hasattr(nfunc, "parser"):
            raise RuntimeError("add_flag should be placed above \"@flags.command()\"")
        nfunc.parser.add_argument(*flag_names, **kwargs)
        return func
    return inner


class FlagCommand(commands.Command):
    async def _parse_flag_arguments(self, ctx):
        argument = ctx.view.read_rest()
        namespace = self.callback.parser.parse_args(shlex.split(argument), ctx=ctx)
        ctx.kwargs.update(vars(namespace))

    async def _parse_arguments(self, ctx):
        ctx.args = [ctx] if self.cog is None else [self.cog, ctx]
        ctx.kwargs = {}
        args = ctx.args
        kwargs = ctx.kwargs

        view = ctx.view
        iterator = iter(self.params.items())

        if self.cog is not None:
            # we have 'self' as the first parameter so just advance
            # the iterator and resume parsing
            try:
                next(iterator)
            except StopIteration:
                fmt = 'Callback for {0.name} command is missing "self" parameter.'
                raise discord.ClientException(fmt.format(self))

        # next we have the 'ctx' as the next parameter
        try:
            next(iterator)
        except StopIteration:
            fmt = 'Callback for {0.name} command is missing "ctx" parameter.'
            raise discord.ClientException(fmt.format(self))

        for name, param in iterator:
            if param.kind == param.POSITIONAL_OR_KEYWORD:
                transformed = await self.transform(ctx, param)
                args.append(transformed)
            elif param.kind == param.KEYWORD_ONLY:
                # kwarg only param denotes "consume rest" semantics
                if self.rest_is_raw:
                    converter = self._get_converter(param)
                    argument = view.read_rest()
                    kwargs[name] = await self.do_conversion(ctx, converter, argument, param)
                else:
                    kwargs[name] = await self.transform(ctx, param)
                break
            elif param.kind == param.VAR_POSITIONAL:
                while not view.eof:
                    try:
                        transformed = await self.transform(ctx, param)
                        args.append(transformed)
                    except RuntimeError:
                        break
            elif param.kind == param.VAR_KEYWORD:
                await self._parse_flag_arguments(ctx)
                break

        if not self.ignore_extra:
            if not view.eof:
                raise commands.TooManyArguments('Too many arguments passed to ' + self.qualified_name)


class FlagGroup(FlagCommand, commands.Group):
    pass
