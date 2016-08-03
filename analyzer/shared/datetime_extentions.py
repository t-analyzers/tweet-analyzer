from datetime import *
import time
import pytz

# coding=utf-8
# write code...

"""
日付を表す文字列とdatetimeオブジェクトを相互に変換するためのユーティリティメソッド
Twitter APIで扱う文字列の形式を対象としている
"""


def now_unix_time():
    """
    現在時刻をUNIX Timeで返す
    :return:
    """
    return time.mktime(datetime.now().timetuple())


def str_to_date_jp(str_date: str) -> datetime:
    """
    日付の文字列を日本時間のdatetimeオブジェクトに変換する
    :param str_date: 日付を表す文字列 EX:'Sun Jul 03 09:50:22 +0000 2016'
    :return: datetimeオブジェクト（タイムゾーンは日本時間）
    """
    dts = datetime.strptime(str_date, '%a %b %d %H:%M:%S +0000 %Y')
    return pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo'))


def utc_str_to_jp_str(str_date: str) -> str:
    """
    UTCの日付文字列を日本時間の日付文字列に変換する
    :param str_date: 日付を表す文字列 EX:'2016-07-03 09:50:22'
    :return: 日付を表す文字列 EX:'2016/07/03 18:50:22'
    """
    dts = datetime.strptime(str_date, '%a %b %d %H:%M:%S +0000 %Y')
    return pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo')).strftime("%Y/%m/%d %H:%M:%S")


def str_to_date(str_date: str) -> datetime:
    """
    日付の文字列をUTC時刻のdatetimeオブジェクトに変換する
    :param str_date: 日付を表す文字列 EX:'2016-07-03 09:50:22'
    :return: datetimeオブジェクト（タイムゾーンはUTC）
    """
    dts = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S')
    return pytz.utc.localize(dts)


def str_to_date_jp_utc(str_date: str) -> datetime:
    """
    日付の文字列（日本時間）をdatetimeオブジェクト（UTC）に変換する
    :param str_date: 日付を表す文字列 EX:'2016-07-03 09:50:22'
    :return: datetimeオブジェクト
    """
    return datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S') - timedelta(hours=9)


def date_to_japan_time(dts: datetime) -> datetime:
    """
    datetimeオブジェクトのtimezoneを日本時間に変換する。
    :param dts: datetimeオブジェクト（UTC）
    :return: datetimeオブジェクト（日本時間）
    """
    return pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo'))


def date_to_japan_time_str(dts: datetime) -> str:
    """
    datetimeオブジェクトを日本時間を表す文字列に変換する
    :param dts: datetimeオブジェクト（UTC）
    :return: 日付を表す文字列（日本時間） EX:'2016-07-03 09:50:22'
    """
    return pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo')).strftime("%Y/%m/%d %H:%M:%S")


def date_to_str(dt: datetime) -> str:
    """
    datetimeオブジェクトを文字列に変換する
    :param dt: datetimeオブジェクト
    :return: 日付を表す文字列 EX:'2016-07-03 09:50:22'
    """
    return dt.strftime("%Y/%m/%d %H:%M:%S")


def str_to_unix_date_jp(str_date: str) -> float:
    """
    日付を表す文字列を日本時間に変換し、UNIX Timeで返す
    :param str_date: 日付を表す文字列 EX:'Sun Jul 03 09:50:22 +0000 2016'
    :return: UNIX Time
    """
    dts = datetime.strptime(str_date, '%a %b %d %H:%M:%S +0000 %Y')
    dt = pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo'))
    return time.mktime(dt.timetuple())


def unix_time_to_datetime(int_date: float) -> datetime:
    """
    UNIX Timeをdatetimeオブジェクトに変換する
    :param int_date: UNIX Time
    :return: datetimeオブジェクト
    """
    return datetime.fromtimestamp(int_date)
