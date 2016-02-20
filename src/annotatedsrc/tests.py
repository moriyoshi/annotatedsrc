import unittest

class CalloutSpecifierTest(unittest.TestCase):
    def test_it(self):
        code = u'''<?php
echo "HEL <--- (1)
LO";
echo "HELLO"; <--- (2)
?>'''
        from .views import extract_callouts, CalloutSpecifier
        code, callouts = extract_callouts(code)
        from pygments.lexers import get_lexer_by_name
        lexer = get_lexer_by_name('php', filters=[CalloutSpecifier(callouts=callouts)])
        print(list(lexer.get_tokens(code)))
