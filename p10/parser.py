#!/usr/bin/env python

import base64

class parser:
    
    _handlers = dict()
    
    def __init__(self):
        self._handlers = dict()
    
    def registerHandler(self, token, handler):
        self._handlers[token] = handler
    
    def _passToHandler(self, origin, token, args):
        try:
            self._handlers[token].handle(origin, args)
        except KeyError:
            raise ParseError("Unknown command", None)
    
    def parse(self, string):
        
        # The standard requires we only accept strings ending in \r\n or \n
        if (string[-1] != "\n"):
            raise ParseError('Line endings were not as expected', string)
        
        if (len(string)) > 512:
            raise ParseError('Line too long to be valid', string)
        string = string.rstrip()
        
        high_level_parts = string.split(None, 2)
        origin = base64.parseNumeric(high_level_parts[0])
        command = high_level_parts[1]
        if not command.isupper():
            raise ParseError('Command not in uppercase', string)
        params = high_level_parts[2]
        if params[0] == ":":
            params = [params[1:]]
        else:
            params = params.split(" :", 1)
            if len(params) == 1:
                last_arg = None
            else:
                last_arg = params[1]
            params = params[0].split(None)
            if last_arg != None:
                params.append(last_arg)
        try:
            self._passToHandler(origin, command, params)
        except ParseError, error:
            raise ParseError(error.value, string)
    
    def build(self, origin, token, args):
        if args[-1].find(" ") > -1:
            build_last_arg = ":" + args[-1]
            build_args = args[0:-1] + build_last_arg.split(" ")
        else:
            build_args = args
        ret = base64.createNumeric(origin) + " " + token + " " + " ".join(build_args) + "\r\n"
        if len(ret) > 512:
            raise ParseError('Line too long to send', ret)
        if not token.isupper():
            raise ParseError('Command not in uppercase during build', ret)
        try:
            self._passToHandler(origin, token, args)
        except ParseError, error:
            raise ParseError(error.value, ret)
        return ret

class ParseError(Exception):
    
    line = ""
    
    def __init__(self, value, line):
        self.value = value
        self.line = line
    
    def __str__(self):
        return repr(self.value) + " on line " + self.line

class ProtocolError(Exception):
    pass
