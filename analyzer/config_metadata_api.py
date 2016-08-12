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
KEY = "50EC1DC40A6418674511100E2072CBF08CE279CB"
MAX_USAGE_COUNT = 100

OUTPUT_FOLDER_PATH = "../out/"
