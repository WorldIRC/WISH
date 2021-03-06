#!/usr/bin/env python

import unittest
from wish.p10.parser import Parser, ParseError, ProtocolError

class CommandHandlerDouble():
    
    def handle(self, origin, line):
        self.rcvd = line
        self.origin = origin

class P10ParserTest(unittest.TestCase):
    
    def testParseSimpleLineSingleArg(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        p.parse("ABAAB TEST foo\r\n")
        self.assertEquals(['foo'], d.rcvd)
    
    def testBuildSimpleLineSingleArg(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertEquals("ABAAB TEST foo\n", p.build((1,1), "TEST", ['foo']))
        
    def testParseSimpleLineTwoArg(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        p.parse("ABAAB TEST foo bar\r\n")
        self.assertEquals(['foo','bar'], d.rcvd)
        
    def testBuildSimpleLineTwoArg(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertEquals("ABAAB TEST foo bar\n", p.build((1,1), "TEST", ['foo','bar']))
    
    def testAcceptJustNewLine(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        p.parse("ABAAB TEST foo\n")
        self.assertEquals(['foo'], d.rcvd)
        
    def testRejectBadLineEndings(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertRaises(ParseError, p.parse, "ABAAB TEST foo")
    
    def testLongArg(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        p.parse("ABAAB TEST :foo bar\r\n")
        self.assertEquals(['foo bar'], d.rcvd)
    
    def testBuildLongArg(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertEquals("ABAAB TEST :foo bar\n", p.build((1,1), "TEST", ['foo bar']))
    
    def testLongArgWithShort(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        p.parse("ABAAB TEST baz :foo bar\r\n")
        self.assertEquals(['baz', 'foo bar'], d.rcvd)
    
    def testBuildLongArgWithShort(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertEquals("ABAAB TEST baz :foo bar\n", p.build((1,1), "TEST", ['baz', 'foo bar']))
    
    def testProtectAgainstLongArgs(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        p.parse("ABAAB TEST b:az :foo bar\r\n")
        self.assertEquals(['b:az', 'foo bar'], d.rcvd)
    
    def testProtectAgainstLongArgsInBuild(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertEquals("ABAAB TEST b:az :foo bar\n", p.build((1,1), "TEST", ['b:az', 'foo bar']))
    
    def testRejectUnknownCommands(self):
        p = Parser({1: 262143})
        self.assertRaises(ParseError, p.parse, "ABAAB TEST foo\r\n")
    
    def testRejectLongLine(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertRaises(ProtocolError, p.parse, "ABAAB TEST baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar\r\n")
    
    def testNoBuildLongLine(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertRaises(ProtocolError, p.build, (1,1), "TEST", ["baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar baz foo bar"])
    
    def testParseFirstLongArg(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        p.parse("ABAAB TEST baz :foo bar: bar bar foo\n")
        self.assertEquals(['baz', 'foo bar: bar bar foo'], d.rcvd)
        
    def testBuildFirstLongArg(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertEquals("ABAAB TEST baz :foo bar: bar bar foo\n", p.build((1,1), "TEST", ['baz', 'foo bar: bar bar foo']))
        
    def testRejectLowercaseCommand(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertRaises(ProtocolError, p.parse, "ABAAB test foo\r\n")
    
    def testCanBuildNumberCommands(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        self.assertEquals("AB 123 baz\n", p.build((1,None), "123", ["baz"]))
        
    def testNoLowercaseCommand(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        self.assertRaises(ProtocolError, p.build, (1,1), "test", ["foo"])
    
    def testOriginSetCorrectly(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        p.parse("ABAAB TEST baz\n")
        self.assertEquals((1,1), d.origin)
    
    def testOriginSetCorrectlyServerOnly(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        p.parse("AB TEST baz\n")
        self.assertEquals((1,None), d.origin)
    
    def testOriginBuildCorrectlyServerOnly(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        self.assertEquals("AB TEST baz\n", p.build((1,None), "TEST", ["baz"]))
    
    def testPreAuthMessage(self):
        p = Parser({1: 262143})
        d = CommandHandlerDouble()
        p.register_handler("TEST", d)
        p.parse_pre_auth("TEST foo bar\r\n", (1, None))
        self.assertEquals(['foo','bar'], d.rcvd)
        self.assertEquals((1, None), d.origin)

def main():
    unittest.main()

if __name__ == '__main__':
    main()
