import inspect
import typing

from discord.ext import commands

from ._default import ParamDefault


class FlagCommand(commands.Command):
    async def _resolve_default(self, ctx, param):
        try:
            if inspect.isclass(param.default) and issubclass(param.default, ParamDefault):
                instance = param.default()
                return await instance.default(ctx)
            elif isinstance(param.default, ParamDefault):
                return await param.default.default(ctx)
        except commands.CommandError:
            raise
        except Exception as e:
            raise commands.ConversionError(param.default, e) from e
        return None if param.default is param.empty else param.default

    async def do_conversion(self, ctx, converter, argument, param):
        try:
            origin = converter.__origin__
        except AttributeError:
            pass
        else:
            if origin is typing.Union:
                errors = []
                _NoneType = type(None)
                for conv in converter.__args__:
                    # if we got to this part in the code, then the previous conversions have failed
                    # so we should just undo the view, return the default, and allow parsing to continue
                    # with the other parameters
                    if conv is _NoneType and param.kind != param.VAR_POSITIONAL:
                        ctx.view.undo()
                        return await self._resolve_default(ctx, param)

                    try:
                        value = await self._actual_conversion(ctx, conv, argument, param)
                    except commands.CommandError as exc:
                        errors.append(exc)
                    else:
                        return value

                # if we're  here, then we failed all the converters
                raise commands.BadUnionArgument(param, converter.__args__, errors)

        return await self._actual_conversion(ctx, converter, argument, param)

    async def transform(self, ctx, param):
        required = param.default is param.empty
        converter = self._get_converter(param)
        consume_rest_is_special = param.kind == param.KEYWORD_ONLY and not self.rest_is_raw
        view = ctx.view
        view.skip_ws()

        # The greedy converter is simple -- it keeps going until it fails in which case,
        # it undos the view ready for the next parameter to use instead
        if type(converter) is commands.converter._Greedy:
            if param.kind == param.POSITIONAL_OR_KEYWORD:
                return await self._transform_greedy_pos(ctx, param, required, converter.converter)
            elif param.kind == param.VAR_POSITIONAL:
                return await self._transform_greedy_var_pos(ctx, param, converter.converter)
            else:
                # if we're here, then it's a KEYWORD_ONLY param type
                # since this is mostly useless, we'll helpfully transform Greedy[X]
                # into just X and do the parsing that way.
                converter = converter.converter

        if view.eof:
            if param.kind == param.VAR_POSITIONAL:
                raise RuntimeError()  # break the loop
            if required:
                raise commands.MissingRequiredArgument(param)
            return await self._resolve_default(ctx, param)

        previous = view.index
        if consume_rest_is_special:
            argument = view.read_rest().strip()
        else:
            argument = view.get_quoted_word()
        view.previous = previous

        return await self.do_conversion(ctx, converter, argument, param)
