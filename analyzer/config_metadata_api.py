# coding=utf-8
# write code...

# mongodb
HOST = "localhost"
PORT = 27017
DB_NAME = "twitter-archive"
INPUT_COLLECTION_NAME = "tweets"
OUTPUT_COLLECTION_NAME = "tweets-metadata"

# metadata Corp. API
NEGAPOSI_URL_ENDPOINT = "http://ap.mextractr.net/negaposi_measure"
EMOTION_URL_ENDPOINT = "http://ap.mextractr.net/emotion_measure"
KEY = "" #metadata株式会社のAPIキー。取得先：　http://www.metadata.co.jp/koseido-negapoji-api.html
MAX_USAGE_COUNT = 100
