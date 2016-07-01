from _datetime import *
import pytz

# coding=utf-8
# write code...


# 現在時刻をUNIX Timeで返す
def now_unix_time():
    return time.mktime(datetime.now().timetuple())


# 日付の文字列をDatetime型で返す
def str_to_date_jp(str_date):
    dts = datetime.strptime(str_date, '%a %b %d %H:%M:%S +0000 %Y')
    return pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo'))


# UTCの日付文字列を日本時間にしてDatetime型で返す
def utc_str_to_jp_str(str_date):
    dts = datetime.strptime(str_date, '%a %b %d %H:%M:%S +0000 %Y')
    return pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo')).strftime("%Y/%m/%d %H:%M:%S")


def str_to_date(str_date):
    dts = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S')
    return pytz.utc.localize(dts)


def str_to_date_jp_utc(str_date):
    return datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S') - timedelta(hours=9)


def date_to_japan_time(dts):
    return pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo'))


def date_to_japan_time_str(dts):
    return pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo')).strftime("%Y/%m/%d %H:%M:%S")


def date_to_str(dt):
    return dt.strftime("%Y/%m/%d %H:%M:%S")


def str_to_unix_date_jp(str_date):
    dts = datetime.strptime(str_date, '%a %b %d %H:%M:%S +0000 %Y')
    dt = pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo'))
    return time.mktime(dt.timetuple())


def unix_time_to_datetime(int_date):
    return datetime.fromtimestamp(int_date)