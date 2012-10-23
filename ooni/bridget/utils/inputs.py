#-*- coding: utf-8 -*-
#
#    inputs.py
#    *********
#
#    "...quis custodiet ipsos custodes?"
#               - Juvenal, Satires VI.347-348 (circa 2nd Century, C.E.)
#
#    :copyright: (c) 2012 Isis Lovecruft
#    :license: see LICENSE for more details.
#    :version: 0.1.0-beta
#

#from types        import FunctionType, FileType
import types

from ooni.bridget import log
from ooni.utils   import date, Storage

class InputFile:
    """
    This is a class describing a file used to store Tor bridge or relays
    inputs. It is a python iterator object, allowing it to be efficiently
    looped.

    This class should not be used directly, but rather its subclasses,
    BridgeFile and RelayFile should be used instead.
    """

    def __init__(self, file, **kw):
        """
        ## This is an InputAsset file, created because you tried to pass a
        ## non-existent filename to a test.
        ##
        ## To use this file, place one input to be tested per line. Each
        ## test takes different inputs. Lines which are commented out with
        ## a '#' are not used.
        """
        self.file    = file
        self.eof     = False
        self.all     = Storage()

        for key, value in input_dict:
            self.all[key] = value

        try:
            self.handler = open(self.file, 'r')
        except IOError:
            with open(self.file, 'w') as explain:
                for line in self.__init__.__doc__:
                    explain.writeline(line)
            self.handler = open(self.file, 'r')
        try:
            assert isinstance(self.handler, file), "That's not a file!"
        except AssertionError, ae:
            log.err(ae)

    # def __handler__(self):
    #     """
    #     Attempt to open InputFile.file and check that it is actually a file.
    #     If it's not, create it and add an explaination for how InputFile files
    #     should be used.

    #     :return:
    #         A :type:`file` which has been opened in read-only mode.
    #     """
    #     try:
    #         handler = open(self.file, 'r')
    #     except IOError, ioerror:             ## not the hacker <(A)3
    #         log.err(ioerror)
    #         explanation = (
    #         with open(self.file, 'w') as explain:
    #             for line in explanation:
    #                 explain.writeline(line)
    #         handler = open(self.file, 'r')
    #     try:
    #         assert isinstance(handler, file), "That's not a file!"
    #     except AssertionError, ae:
    #         log.err(ae)
    #     else:
    #         return handler

    def __iter__(next, StopIteration):
        """
        Returns the next input from the file.
        """
        #return self.next()
        return self

    def len(self):
        """
        Returns the number of the lines in the InputFile.
        """
        with open(self.file, 'r') as input_file:
            lines = input_file.readlines()
            for number, line in enumerate(lines):
                self.input_dict[number] = line
        return number + 1

    def next(self):
        try:
            return self.next_input()
        except:
            raise StopIteration

    def next_input(self):
        """
        Return the next input.
        """
        line = self.handler.readline()
        if line:
            parsed_line = self.parse_line(line)
            if parsed_line:
                return parsed_line
        else:
            self.fh.seek(0)
            raise StopIteration

    def default_parser(self, line):
        """
        xxx fill me in
        """
        if not line.startswith('#'):
            return line.replace('\n', '')
        else:
            return False

    def parse_line(self, line):
        """
        Override this method if you need line by line parsing of an Asset.

        The default parsing action is to ignore lines which are commented out
        with a '#', and to strip the newline character from the end of the
        line.

        If the line was commented out return an empty string instead.

        If a subclass Foo incorporates another class Bar, when Bar is not
        also a subclass of InputFile, and Bar.parse_line() exists, then
        do not overwrite Bar's parse_line method.
        """
        assert not hasattr(super(InputFile, self), 'parse_line')

        if self.parser is None:
            if not line.startswith('#'):
                return line.replace('\n', '')
            else:
                return ''
        else:
            try:
                assert isinstance(self.parser, FunctionType),"Not a function!"
            except AssertionError, ae:
                log.err(ae)
            else:
                return self.parser(line)

class BridgeFile(InputFile):
    """
    xxx fill me in
    """
    def __init__(self, **kw):
        super(BridgeFile, self).__init__(**kw)

class MissingInputException(Exception):
    """

    Raised when an :class:`InputFile` necessary for running the Test is
    missing.

    """
    def __init__(self, error_message):
        print error_message
        import sys
        return sys.exit()
