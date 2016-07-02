import pymongo

import config as config

# coding=utf-8
# write code...


def connect_tweet_collection():
    client = pymongo.MongoClient(config.HOST, config.PORT)
    return client[config.DB_NAME][config.COLLECTION_NAME]