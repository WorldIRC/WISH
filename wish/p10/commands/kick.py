#!/usr/bin/env python

from wish.p10.commands.basecommand import BaseCommand
from wish.p10.base64 import parse_numeric

class KickHandler(BaseCommand):
    
    def handle(self, origin, args):
        self._state.kick(
            origin,
            args[0],
            parse_numeric(args[1], self._state.max_client_numerics),
            args[-1]
        )
