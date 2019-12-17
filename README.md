# Flag Parsing
A util for discord.py bots that allow passing flags into commands.

To install, run the following command:
```
pip install discord-flags
```

Basic example usage:

```python
import discord
from discord.ext import flags, commands

bot = commands.Bot("!")

# Invocation: !flags --count=5 --string "hello world" --user Xua --thing y

@flags.add_flag("--count", type=int, default=10)
@flags.add_flag("--string", default="hello!")
@flags.add_flag("--user", type=discord.User)
@flags.add_flag("--thing", type=bool)
@flags.command()
async def flags(ctx, **flags):
    await ctx.send("--count={count!r}, --string={string!r}, --user={user!r}, --thing={thing!r}".format(**flags))
bot.add_command(flags)
```

Important note that `@flags.command` MUST be under all `@flags.add_flag`
decorators.

`@flags.add_flag` takes the same arguments as `argparse.ArgumentParser.add_argument`
to keep things simple.