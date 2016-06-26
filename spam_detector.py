from collections import defaultdict
from date_utilities import *
import db
import re
from logger import Logger

# coding=utf-8
# write code...

logger = Logger("spam_detector")
tweet_collection = db.connect_tweet_collection()


def select_outlier_retweet_num_per_hour(from_str_datetime_jp, limit=120):
    result_list = []
    from_date = str_to_date_jp_utc(from_str_datetime_jp)
    to_date = str_to_date_jp_utc(from_str_datetime_jp) + timedelta(hours=1)

    for tweet in tweet_collection.find({'retweeted_status': {"$ne": None},
                                        'created_datetime': {"$gte": from_date, "$lt": to_date}},
                                       {'user': 1, 'text': 1, 'entities': 1, 'created_at': 1, 'id': 1}):

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
    return {k: v for k, v in sorted_dict if v > limit}


def detect_spam_user(from_date, to_date):
    d_diff = to_date - from_date
    d_hours = (d_diff.days * 24) + (d_diff.seconds / float(3600))
    user_name_set = set()

    for hours in range(int(d_hours)):
        d = (from_date + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        result = select_outlier_retweet_num_per_hour(d, limit=60)
        if len(result) > 0:
            [user_name_set.add(key) for key in result.keys()]
            logger.info('detect spam {0} {1}'.format(d, result))
            print(d, result)

    return user_name_set


def divide_spam_tweet(spam_users):
    count = 0
    retweeted_name = ""
    spam_twitter = set()

    for tweet in tweet_collection.find({'retweeted_status': {"$ne": None}}):
        try:
            retweeted_name = tweet['entities']['user_mentions'][0]['screen_name']
        except Exception as e:
            logger.info('handle {0}'.format(type(e)))
            count += 1
            pattern = r".*@([0-9a-zA-Z_]*).*"
            ite = re.finditer(pattern, tweet['text'])

            for it in ite:
                retweeted_name = it.group(1)
                break

        if retweeted_name in spam_users:
            # スパムアカウントへのリツイートにspamフラグを付与
            tweet_collection.update({'_id': tweet['_id']}, {'$set': {'spam': True}})
            # スパムツイートをしたアカウントもブラックリスト入り
            spam_twitter.add(tweet['user']['screen_name'])

    msg = '{0}件のリツイートをスパムに分類しました'.format(count)
    logger.info(msg)
    print(msg)

    # ブラックリスト入りのユーザーのツイートをスパムに分類
    count = 0
    for tweet in tweet_collection.find({}, {'user.screen_name': 1}):
        sc_name = tweet['user']['screen_name']
        if sc_name in spam_twitter:
            count += 1
            tweet_collection.update({'_id': tweet['_id']}, {'$set': {'spam': True}})
    msg = '{0}件のツイートをスパムに分類しました'.format(count)
    logger.info(msg)
    print(msg)


if __name__ == '__main__':
    today = datetime.today()
    next_day = today + timedelta(days=1)
    last_month = next_day - timedelta(days=31)
    date_format = "%Y-%m-%d 00:00:00"

    print("{0}〜{1}間のスパムツイートを検索します。"
          .format(last_month.strftime(date_format), next_day.strftime(date_format)))

    divide_spam_tweet(detect_spam_user(str_to_date_jp_utc(last_month.strftime(date_format)),
                                       str_to_date_jp_utc(next_day.strftime(date_format))))