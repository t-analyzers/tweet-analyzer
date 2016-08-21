#!/usr/bin/env python
# -*- coding: utf-8 -*-

from shared.log import Log
import pymongo
import config as config


class BaseAnalyzer(object):
    """
    MongoDBへのアクセス機能とログ出力機能をもつ基本クラス
    """

    def __init__(self):
        self.log = Log(self.__class__.__name__)
        self.__tweets = None

    @property
    def tweets(self):
        """
        :return: つぶやきを保存しているMongoDBのコレクション
        """
        if self.__tweets is None:
            client = pymongo.MongoClient(config.HOST, config.PORT)
            self.__tweets = client[config.DB_NAME][config.COLLECTION_NAME]

        return self.__tweets

    @property
    def last_tweet(self):
        """
        :return: 保存済のつぶやきの中で最も新しいつぶやき
        """
        return self.tweets.find_one(sort=[["id", pymongo.DESCENDING]])
