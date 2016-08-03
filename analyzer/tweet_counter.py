from collections import defaultdict

import pandas as pd
from pandas import DataFrame, Series

from base_analyzer import BaseAnalyzer
from shared.datetime_extentions import *
from shared.decorators import trace

# coding=utf-8
# write code...


class TweetCounter(BaseAnalyzer):
    """
    時間帯ごとのつぶやき数を集計するクラス
    """

    def __init__(self):
        super().__init__()

    @trace()
    def get_time_series_data(self, search_condition: dict, date_format: str) -> DataFrame:
        """
        日付フォーマットに合致するつぶやき数を集計し、DataFrameにまとめて返す
        :param search_condition: 検索の絞り込み条件
        :param date_format: 日付フォーマット、指定されたフォーマットごとにつぶやき数を集計する
        :return: DataFrame
        """

        all_date_dict = defaultdict(int)
        ret_date_dict = defaultdict(int)
        norm_date_dict = defaultdict(int)
        spam_dict = defaultdict(int)
        not_spam_all_dict = defaultdict(int)
        not_spam_norm_dict = defaultdict(int)
        not_spam_ret_dict = defaultdict(int)

        for tweet in self.tweets.find(search_condition,
                                      {'_id': 1, 'created_datetime': 1, 'retweeted_status': 1, 'spam': 1}):

            str_date = date_to_japan_time(tweet['created_datetime']).strftime(date_format)
            all_date_dict[str_date] += 1

            # spamの除去
            if ('spam' in tweet) and (tweet['spam'] is True):
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
        df.columns = ['#ALL', '#NotRT', '#RT', '#spam',
                      '#ALL(exclude spam)', '#NotRT(exclude spam)', '#RT(exclude spam)']
        return df
