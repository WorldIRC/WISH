#!/usr/bin/env python

from wish.p10.commands.basecommand import BaseCommand
from wish.p10.base64 import parse_numeric

class VersionHandler(BaseCommand):
    
    def handle(self, origin, args):
        self._state.request_version(
            origin,
            parse_numeric(args[0], self._state.max_client_numerics)
        )
