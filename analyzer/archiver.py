#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
from tweepy import API, OAuthHandler, TweepError
from tweepy.parsers import JSONParser

import conf.config_archiver as config
from base_analyzer import BaseAnalyzer
from shared.datetime_extentions import *
from shared.decorators import trace


class TweetArchiver(BaseAnalyzer):
    """
    つぶやきをMongoDBに保存するクラス
    """

    def __init__(self):
        super().__init__()

    @trace()
    def archive(self):
        """
        DBにつぶやきを保存し、UTCから日本時間を算出し、セットする。
        :return: なし
        """
        self._insert_tweets()
        self._add_jp_datetime_info()

    def _insert_tweets(self):
        """
        Twitter APIを用いてつぶやきを検索し、MongoDBに保存する。
        :return: なし
        """
        twitter_client = self._create_twitter_client()

        # 取得済のつぶやきの中から最新のつぶやきを取得し、そのつぶやきのid以降を取得するように設定しておく。
        since_id = None if self.last_tweet is None else self.last_tweet["id"]

        # 初回の検索時は、max_idの設定をしないように-1を設定しておく。
        max_id = -1
        tweet_count = 0
        # リトライ用のカウンタ
        retry_count = 0
        max_retry_count = 5

        query_string = self._get_query_string()

        self.log.info("Downloading tweets")
        while True:
            try:
                params = {
                    "q": query_string,
                    "count": 100,
                    "lang": "ja",
                    "result_type": "recent"
                }
                # max_idとsince_idは設定されている場合のみ、パラメータとして渡すようにする。
                if max_id > 0:
                    params["max_id"] = str(max_id - 1)
                if since_id is not None:
                    params["since_id"] = since_id
                if config.PROXY:
                    params["proxy"] = config.PROXY

                search_result = twitter_client.search(**params)
                statuses = search_result["statuses"]

                # 最後まで検索できたかチェック
                if statuses is None or len(statuses) == 0:
                    print("No more tweets found")
                    self.log.info("No more tweets found")
                    break

                tweet_count += len(statuses)
                print("Downloaded {0} tweets".format(tweet_count))
                self.log.debug("Downloaded {0} tweets".format(tweet_count))

                result = self.tweets.insert_many(statuses)
                self.log.debug("Result of insert into mongodb = {0}".format(result))

                # 最後に取得したTweetのIDで更新する。
                max_id = statuses[-1]["id"]

            except TweepError as e:
                print(str(e))
                self.log.debug("Failed to call, in retry({0}/{1})".format(retry_count, max_retry_count))
                self.log.exception(str(e))
                if retry_count >= max_retry_count:
                    break
                else:
                    retry_count += 1
                    time.sleep(10)
            except Exception as e:
                print(str(e))
                self.log.exception(str(e))
                break

    @staticmethod
    def _get_query_string() -> str:
        """
        YAMLファイルから検索キーワードのリストを取得し、Twitter検索用にOR連結した文字列を返す
        :return: Twitter検索キーワード
        """
        with open("conf/search_keywords.yml", "r", encoding="utf-8") as file:
            keywords = yaml.load(file)
        # 検索キーワードに半角スペースが含まれている（OR条件あり）の場合、括弧で囲む。
        return " OR ".join(["(" + keyword + ")" if " " in keyword else keyword for keyword in keywords])

    def _create_twitter_client(self) -> API:
        """
        tweepyのAPIを生成する
        :return: API
        """
        # Twitter検索用のクライアント生成
        auth = OAuthHandler(config.CONSUMER_KEY, config.CONSUMER_SECRET)
        auth.set_access_token(config.ACCESS_TOKEN_KEY, config.ACCESS_TOKEN_SECRET)
        # JSONで結果を受け取りたいので、JSONParserを設定する。
        # 検索の上限に達してもライブラリ側でよろしくやってくれる。はず。
        twitter_api = API(auth, parser=JSONParser(), wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

        if twitter_api is None:
            self.log.error("Can't Authenticate")
            sys.exit(-1)

        return twitter_api

    def _add_jp_datetime_info(self):
        """
        Twitter APIで取得したつぶやきはUTC時刻となっているため、日本時間に変換した値もセットしておく。
        すでにセット済の場合は、なにもしない。
        :return: なし
        """
        for tweet in self.tweets.find({"created_datetime": {"$exists": False}}, {"_id": 1, "created_at": 1}):
            self.tweets.update({"_id": tweet["_id"]},
                               {"$set": {"created_datetime": str_to_date_jp(tweet["created_at"])}})
        self.log.info("Adding Datetime info")
