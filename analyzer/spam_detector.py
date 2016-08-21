#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from collections import defaultdict

from base_analyzer import BaseAnalyzer
from shared.datetime_extentions import *
from shared.decorators import trace


class SpamDetector(BaseAnalyzer):
    """
    スパム判定するクラス
    """

    def __init__(self):
        super().__init__()

    @trace()
    def divide_spam_tweet(self, start_datetime: datetime, end_datetime: datetime, limit_tweet_count: int):
        """
        スパムツィートを検索し、該当するツィートに対してスパムフラグを設定する
        :param start_datetime: 検索対象の開始時刻
        :param end_datetime: 検索対象の終了時刻
        :param limit_tweet_count: スパム判定に使用する1時間あたりのリツィート回数
        :return: なし
        """
        count = 0
        retweeted_name = ""
        spam_twitter = set()
        date_format = "%Y-%m-%d 00:00:00"

        print("{0}〜{1}間のスパムツイートを検索します。"
              .format(start_datetime.strftime(date_format), end_datetime.strftime(date_format)))
        print("1時間に{0}回以上リツィートされたものはスパムと判定します。".format(limit_tweet_count))
        spam_users = self._detect_spam_user(str_to_date_jp_utc(start_datetime.strftime(date_format)),
                                            str_to_date_jp_utc(end_datetime.strftime(date_format)),
                                            limit_tweet_count)

        for tweet in self.tweets.find({'retweeted_status': {"$ne": None},
                                       'created_datetime': {"$gte": start_datetime, "$lt": end_datetime}}):
            try:
                retweeted_name = tweet['entities']['user_mentions'][0]['screen_name']
            except Exception as e:
                self.log.info('handle {0}'.format(type(e)))
                count += 1
                pattern = r".*@([0-9a-zA-Z_]*).*"
                ite = re.finditer(pattern, tweet['text'])

                for it in ite:
                    retweeted_name = it.group(1)
                    break

            if retweeted_name in spam_users:
                # スパムアカウントへのリツイートにspamフラグを付与
                self.tweets.update({'_id': tweet['_id']}, {'$set': {'spam': True}})
                # スパムツイートをしたアカウントもブラックリスト入り
                spam_twitter.add(tweet['user']['screen_name'])

        msg = '{0}件のリツイートをスパムに分類しました'.format(count)
        self.log.info(msg)
        print(msg)

        # ブラックリスト入りのユーザーのツイートをスパムに分類
        count = 0
        for tweet in self.tweets.find({'created_datetime': {"$gte": start_datetime, "$lt": end_datetime}},
                                      {'user.screen_name': 1}):
            sc_name = tweet['user']['screen_name']
            if sc_name in spam_twitter:
                count += 1
                self.tweets.update({'_id': tweet['_id']}, {'$set': {'spam': True}})
        msg = '{0}件のツイートをスパムに分類しました'.format(count)
        self.log.info(msg)
        print(msg)

    def _detect_spam_user(self, from_date: datetime, to_date: datetime, limit_tweet_count: int):
        d_diff = to_date - from_date
        d_hours = (d_diff.days * 24) + (d_diff.seconds / float(3600))
        user_name_set = set()

        # DBへのアクセス頻度を減らすために先に対象ツィート全て取得しておく
        all_tweets = [{'user': tweet['user'], 'text': tweet['text'], 'entities': tweet['entities'],
                       'created_at': tweet['created_at'], 'utc_date': utc_str_to_date(tweet['created_at'])}
                      for tweet in self.tweets.find({'retweeted_status': {"$ne": None},
                                                     'created_datetime': {"$gte": from_date, "$lt": to_date}},
                                                    {'user': 1, 'text': 1, 'entities': 1, 'created_at': 1})]

        for hours in range(int(d_hours)):
            d = (from_date + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
            begin = str_to_date_jp_utc(d)
            end = begin + timedelta(hours=1)
            # 1時間単位で絞り込む
            target_tweets = [x for x in all_tweets if begin <= x['utc_date'] <= end]
            result = self._select_outlier_retweet_num_per_hour(target_tweets, limit_tweet_count)
            if len(result) > 0:
                [user_name_set.add(key) for key in result.keys()]
                self.log.info('detect spam {0} {1}'.format(d, result))
                print(d, result)

        return user_name_set

    def _select_outlier_retweet_num_per_hour(self, tweets: list, limit_tweet_count: int):
        result_list = []
        for tweet in tweets:
            mentioned_username = ""
            if len(tweet['entities']['user_mentions']) != 0:
                mentioned_username = tweet['entities']['user_mentions'][0]['screen_name']

            result_list.append({"created_at": utc_str_to_jp_str(tweet['created_at']),
                                "screen_name": tweet['user']['screen_name'],
                                "referred_name": mentioned_username,
                                "text": tweet['text'].replace('\n', ' ')})

        name_dict = defaultdict(int)
        for result in result_list:
            name_dict[result['referred_name']] += 1

        # リツイート回数でソート
        sorted_dict = sorted(name_dict.items(), key=lambda x: x[1])
        # リツイート元ユーザー名, リツイート回数(limitを超えたもの)
        return {k: v for k, v in sorted_dict if v > limit_tweet_count}
