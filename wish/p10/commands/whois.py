#!/usr/bin/env python

from wish.p10.commands.basecommand import BaseCommand
from wish.p10.base64 import parse_numeric

class WhoIsHandler(BaseCommand):
    
    def handle(self, origin, args):
        for search in args[1].split(","):
            self._state.request_whois(
                origin,
                parse_numeric(args[0], self._state.max_client_numerics),
                search
            )
