from collections import defaultdict

import pandas as pd
from pandas import DataFrame, Series

from date_ext import *
from db import *


# coding=utf-8
# write code...


def get_time_series_data(condition, date_format) -> DataFrame:
    """
    日付フォーマットに合致するつぶやき数をDataFrameにまとめて返す
    :param condition: 検索の絞り込み条件（Dictionary）
    :param date_format: 日付フォーマット、指定されたフォーマットごとにつぶやき数を計算する
    :return: DataFrame
    """
    tweet_collection = connect_tweet_collection()

    all_date_dict = defaultdict(int)
    ret_date_dict = defaultdict(int)
    norm_date_dict = defaultdict(int)
    spam_dict = defaultdict(int)
    not_spam_all_dict = defaultdict(int)
    not_spam_norm_dict = defaultdict(int)
    not_spam_ret_dict = defaultdict(int)

    for tweet in tweet_collection.find(condition, {'_id': 1, 'created_datetime': 1, 'retweeted_status': 1, 'spam': 1}):
        str_date = date_to_japan_time(tweet['created_datetime']).strftime(date_format)
        all_date_dict[str_date] += 1

        # spamの除去
        if ('spam' in tweet) and (tweet['spam'] == True):
            spam_dict[str_date] += 1
            not_spam_all_dict[str_date] += 0
        else:
            spam_dict[str_date] += 0
            not_spam_all_dict[str_date] += 1
            # spamでないもののRetweet数のカウント
            if 'retweeted_status' not in tweet:
                not_spam_ret_dict[str_date] += 0
                not_spam_norm_dict[str_date] += 1
            elif tweet['retweeted_status'] is not None:
                not_spam_ret_dict[str_date] += 1
                not_spam_norm_dict[str_date] += 0
            else:
                not_spam_ret_dict[str_date] += 0
                not_spam_norm_dict[str_date] += 1

        if 'retweeted_status' not in tweet:
            ret_date_dict[str_date] += 0
            norm_date_dict[str_date] += 1
        elif tweet['retweeted_status'] is not None:
            ret_date_dict[str_date] += 1
            norm_date_dict[str_date] += 0
        else:
            ret_date_dict[str_date] += 0
            norm_date_dict[str_date] += 1

    df = pd.concat([Series(all_date_dict), Series(norm_date_dict), Series(ret_date_dict), Series(spam_dict),
                    Series(not_spam_all_dict), Series(not_spam_norm_dict), Series(not_spam_ret_dict)], axis=1)
    df.columns = ['#ALL', '#NotRT', '#RT', '#spam', '#ALL(exclude spam)', '#NotRT(exclude spam)', '#RT(exclude spam)']
    return df
