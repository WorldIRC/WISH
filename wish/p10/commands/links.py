#!/usr/bin/env python

from wish.p10.base64 import parse_numeric
from wish.p10.commands.basecommand import BaseCommand

class LinksHandler(BaseCommand):
    """
    Returns link information about the server
    """
    
    def handle(self, origin, args):
        self._state.request_links(
            origin,
            parse_numeric(args[0], self._state.max_client_numerics),
            args[1]
        )
