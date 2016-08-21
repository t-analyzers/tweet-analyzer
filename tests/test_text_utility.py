#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analyzer.shared.text_utility as util


class TestTextUtility(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_text_eliminated_some_pattern_words(self):
        testcase_sources = [
            ("@hoge moge", "moge"),
            ("http://localhost moge", "moge"),
            ("http://localhost\nmoge", "\nmoge"),
            ("#hoge moge", "moge"),
            ("#hoge\nmoge", "\nmoge"),
            ("あいうABCDEF1234えお", "あいうえお"),
            ("あいうABCDEF12えお", "あいうえお"),
        ]
        for source, expected in testcase_sources:
            with self.subTest(source=source, expected=expected):
                eliminated_text = util.get_text_eliminated_some_pattern_words(source)
                self.assertEqual(eliminated_text, expected)

    def test_get_nps_printid(self):
        testcase_sources = [
            ("あいうえお", []),
            # 10桁の予約番号は除外される
            ("あいうABCDEF1234えお", []),
            ("あいうABCDEF12えお", ["ABCDEF12"]),
            ("あいうABCDEF12えおABCDEF12", ["ABCDEF12", "ABCDEF12"])
        ]
        for source, expected in testcase_sources:
            with self.subTest(source=source, expected=expected):
                nps_id = util.get_nps_printid(source)
                self.assertEqual(nps_id, expected)

    def test_get_eliminated_text(self):
        testcase_sources = [
            ("あいうABCDEF12えお", "あいうえお"),
            ("あいうえお", "あいうえお")
        ]
        for source, expected in testcase_sources:
            with self.subTest(source=source, expected=expected):
                eliminated_text = util.get_eliminated_text(util.NPS_ID_PATTERN, source)
                self.assertEqual(eliminated_text, expected)

if __name__ == '__main__':
    unittest.main()
