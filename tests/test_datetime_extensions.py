import os
import sys
import unittest
from datetime import datetime
import time
import pytz

# パスに追加することで、importできるようにする。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analyzer.shared.datetime_extentions as ext

# coding=utf-8
# write code...


class TestDatetimeExtensions(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_now_unix_time(self):
        unix_time = ext.now_unix_time()
        self.assertIsInstance(unix_time, float)

    def test_str_to_date_jp(self):
        jp_date = ext.str_to_date_jp('Sun Jul 03 09:50:22 +0000 2016')
        expected = datetime(2016, 7, 3, hour=18, minute=50, second=22, tzinfo=pytz.timezone('Asia/Tokyo'))
        self.assertEqual(jp_date, expected)

    def test_str_to_date(self):
        utc_date = ext.str_to_date('2016-07-03 09:50:22')
        expected = datetime(2016, 7, 3, hour=9, minute=50, second=22, tzinfo=pytz.timezone('UTC'))
        self.assertEqual(utc_date, expected)

    def test_str_to_date_jp_utc(self):
        utc_date = ext.str_to_date_jp_utc('2016-07-03 09:50:22')
        expected = datetime(2016, 7, 3, hour=0, minute=50, second=22)
        self.assertEqual(utc_date, expected)

    def test_utc_str_to_jp_str(self):
        jp_date = ext.utc_str_to_jp_str('Sun Jul 03 09:50:22 +0000 2016')
        expected = '2016/07/03 18:50:22'
        self.assertEqual(jp_date, expected)

    def test_date_to_japan_time(self):
        target = datetime(2016, 8, 2, hour=15, minute=30, second=10, microsecond=100)
        expected = datetime(2016, 8, 3, hour=0, minute=30, second=10, microsecond=100,
                            tzinfo=pytz.timezone('Asia/Tokyo'))
        jp_time = ext.date_to_japan_time(target)
        self.assertEqual(jp_time, expected)

    def test_date_to_japan_time_str(self):
        target = datetime(2016, 8, 2, hour=15, minute=30, second=10, microsecond=100)
        jp_time_str = ext.date_to_japan_time_str(target)
        self.assertEqual(jp_time_str, '2016/08/03 00:30:10')

    def test_date_to_str(self):
        target = datetime(2016, 8, 2, hour=15, minute=30, second=10, microsecond=100)
        time_str = ext.date_to_str(target)
        self.assertEqual(time_str, '2016/08/02 15:30:10')

    def test_str_to_unix_date_jp(self):
        unix_time = ext.str_to_unix_date_jp('Sun Jul 03 09:50:22 +0000 2016')
        self.assertIsInstance(unix_time, float)

    def test_unix_time_to_datetime(self):
        # UNIX Timeに変換するときはmicrosecondの精度では変換できないので注意
        expected = datetime(2016, 8, 2, hour=15, minute=30, second=10)
        unix_time = time.mktime(expected.timetuple())
        self.assertEqual(ext.unix_time_to_datetime(unix_time), expected)

if __name__ == '__main__':
    unittest.main()
