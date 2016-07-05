from collections import defaultdict

import pandas as pd
from pandas import DataFrame, Series

from shared.datetime_extentions import *
from shared.mongo_wrapper import *
from shared.log import Log

# coding=utf-8
# write code...


class SimpleAnalyzer(object):
    """
    簡単な集計を行い、DataFrameを作成するクラス
    """
    def __init__(self):
        self.__log = Log("spam_detector")
        self.__tweets = MongoWrapper.connect_tweets()

    def get_text_data(self, search_condition: dict) -> DataFrame:
        """
        つぶやきの内容をMongoDBから取得する
        :param search_condition: 検索の絞り込み条件
        :return: DataFrame
        """

        date_format = '%Y/%m/%d %a %H:%M:%S'
        results = [
            {'created_datetime': date_to_japan_time(tweet['created_datetime']).strftime(date_format),
             'retweet_count': tweet['retweet_count'], 'id': tweet['id'],
             'user.screen_name': tweet['user']['screen_name'], 'text': tweet['text']}
            for tweet in self.__tweets.find(search_condition,
                                            {'created_datetime': 1, 'retweet_count': 1, 'id': 1, 'user': 1, 'text': 1})]

        df = DataFrame(results, columns=['created_datetime', 'retweet_count', 'id', 'user.screen_name', 'text'])
        df.sort_values(by='created_datetime', ascending=False).reset_index(drop=True)
        return df

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

        for tweet in self.__tweets.find(search_condition,
                                        {'_id': 1, 'created_datetime': 1, 'retweeted_status': 1, 'spam': 1}):

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
        df.columns = ['#ALL', '#NotRT', '#RT', '#spam',
                      '#ALL(exclude spam)', '#NotRT(exclude spam)', '#RT(exclude spam)']
        return df
