from disco.bot import Plugin

import contextlib
import io
import textwrap
import traceback


class eval(Plugin):
    @Plugin.command('eval', '[code:str...]')
    def eval(self, event, code):
        env = {
            'self': self,
            'bot': self.bot,
            'event': event,
            'msg': event.msg
        }

        env.update(globals())

        if code.startswith('```'):
            code = "\n".join(code.split("\n")[1:-1])

        out = io.StringIO()

        to_compile = f'def func():\n{textwrap.indent(code, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return event.msg.reply(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with contextlib.redirect_stdout(out):
                ret = func()
        except Exception as e:
            value = out.getvalue()
            event.msg.reply(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = out.getvalue()
            if ret is None:
                if value:
                    event.msg.reply(f'```py\n{value}\n```')
            else:
                event.msg.reply(f'```py\n{value}{ret}\n```')