import sys
import yaml
from pymongo import *
from tweepy import API, OAuthHandler, TweepError
from tweepy.parsers import JSONParser
import config
from date_utilities import *
from logger import Logger


# coding: UTF-8
# write code...

logger = Logger("archive")

client = MongoClient(config.HOST, config.PORT)
tweets = client[config.DB_NAME][config.COLLECTION_NAME]


def get_twitter_client() -> API:
    # Twitter検索用のクライアント生成
    auth = OAuthHandler(config.CONSUMER_KEY, config.CONSUMER_SECRET)
    auth.set_access_token(config.ACCESS_TOKEN_KEY, config.ACCESS_TOKEN_SECRET)
    # JSONで結果を受け取りたいので、JSONParserを設定する。
    # 検索の上限に達してもライブラリ側でよろしくやってくれる。はず。
    twitter_api = API(auth, parser=JSONParser(), wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

    if twitter_api is None:
        logger.error("Can't Authenticate")
        sys.exit(-1)

    return twitter_api


def archive():
    # YAMLファイルから検索キーワードのリストを読み取り、OR検索用の文字列を生成する。
    with open("search_keywords.yml", "r") as file:
        keywords = yaml.load(file)
    query_string = " OR ".join(keywords)

    twitter_client = get_twitter_client()

    # 取得済のつぶやきの中から最新のつぶやきを取得し、そのつぶやきのid以降を取得するように設定しておく。
    last_tweet = tweets.find_one(sort=[["id", DESCENDING]])
    since_id = None if last_tweet is None else last_tweet["id"]

    # 初回の検索時は、max_idの設定をしないように-1を設定しておく。
    max_id = -1

    # tweet_countがmax_tweet_countまで達したら、検索を終了する。
    # max_tweet_countには大きな値を設定しておく。
    tweet_count = 0
    max_tweet_count = 100000

    logger.info("Downloading max {0} tweets".format(max_tweet_count))
    while tweet_count < max_tweet_count:
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

            search_result = twitter_client.search(**params)
            statuses = search_result["statuses"]

            # 最後まで検索できたかチェック
            if statuses is None or len(statuses) == 0:
                print("No more tweets found")
                logger.info("No more tweets found")
                break

            tweet_count += len(statuses)
            print("Downloaded {0} tweets".format(tweet_count))
            logger.debug("Downloaded {0} tweets".format(tweet_count))

            result = tweets.insert_many([status for status in statuses])
            logger.debug("Result of insert into mongodb = {0}".format(result))

            # 最後に取得したTweetのIDで更新する。
            max_id = statuses[-1]["id"]

        except (TypeError, TweepError) as e:
            print(str(e))
            logger.exception(str(e))
            break


def add_jp_datetime_info():
    print("Adding Datetime info")
    logger.info("Adding Datetime info")
    [tweets.update({"_id": tweet["_id"]}, {"$set": {"created_datetime": str_to_date_jp(tweet["created_at"])}})
     for tweet in tweets.find({"created_datetime": {"$exists": False}}, {"_id": 1, "created_at": 1})]


if __name__ == '__main__':
    archive()
    add_jp_datetime_info()

