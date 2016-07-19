from pandas import DataFrame

from base_analyzer import BaseAnalyzer
from shared.datetime_extentions import *
from shared.decorators import trace

# coding=utf-8
# write code...


class SampleAnalyzer(BaseAnalyzer):
    """
    サンプルの分析用クラス
    """
    def __init__(self):
        super().__init__()

    @trace()
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
            for tweet in self.tweets.find(search_condition,
                                          {'created_datetime': 1, 'retweet_count': 1, 'id': 1, 'user': 1, 'text': 1})
            ]

        df = DataFrame(results, columns=['created_datetime', 'retweet_count', 'id', 'user.screen_name', 'text'])
        df.sort_values(by='created_datetime', ascending=False).reset_index(drop=True)
        return df
