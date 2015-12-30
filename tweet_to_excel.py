from collections import defaultdict
import pandas as pd
from pandas import DataFrame, Series
import config
from pymongo import MongoClient
from date_utilities import *
from logger import Logger
import yaml

# coding=utf-8
# write code...

logger = Logger("excel")
client = MongoClient(config.HOST, config.PORT)
tweets = client[config.DB_NAME][config.COLLECTION_NAME]


def get_time_series_data(date_format) -> DataFrame:
    # 時系列ツイート数データの表示
    all_date_dict = defaultdict(int)
    ret_date_dict = defaultdict(int)
    norm_date_dict = defaultdict(int)

    for tweet in tweets.find({}, {"_id": 1, "created_datetime": 1, "retweeted_status": 1}):
        str_date = date_to_japan_time(tweet['created_datetime']).strftime(date_format)
        all_date_dict[str_date] += 1

        # Retweet数のカウント
        if "retweeted_status" not in tweet:
            ret_date_dict[str_date] += 0
            norm_date_dict[str_date] += 1
        elif tweet["retweeted_status"] is not None:
            ret_date_dict[str_date] += 1
            norm_date_dict[str_date] += 0
        else:
            ret_date_dict[str_date] += 0
            norm_date_dict[str_date] += 1

    df = pd.concat([Series(all_date_dict), Series(norm_date_dict), Series(ret_date_dict)], axis=1)
    df.columns = ["#ALL", "#NotRT", "#RT"]

    return df


def get_tweet_text_data() -> DataFrame:
    result_list = [{"created_datetime": tweet["created_datetime"], "retweet_count": tweet['retweet_count'],
                    "id": tweet['id'], "user.screen_name": tweet["user"]["screen_name"], "text": tweet["text"]}
                   for tweet
                   in tweets.find({}, {"created_datetime": 1, "retweet_count": 1, "id": 1, "user": 1, "text": 1})]

    return DataFrame(result_list, columns=["created_datetime", "retweet_count", "id", "user.screen_name", "text"])


def write_worksheet(excel_writer, data_frame, sheet_name):
    data_frame.to_excel(excel_writer, sheet_name=sheet_name)
    print('wrote worksheet {0}'.format(sheet_name))
    logger.info('wrote worksheet {0}'.format(sheet_name))


def create_excel_workbook(excel_file_path):
    try:
        print("start a creating {0}".format(excel_file_path))
        # Excelを作成するためのオブジェクトを初期化
        excel_writer = pd.ExcelWriter(excel_file_path, engine="xlsxwriter")

        # 1時間ごとのつぶやき数
        write_worksheet(excel_writer, get_time_series_data("%Y %m/%d %H %a"), "1時間ごとのつぶやき数")
        # 日ごとのつぶやき数
        write_worksheet(excel_writer, get_time_series_data("%Y %m/%d"), "日ごとのつぶやき数")
        # 時間帯別のつぶやき数
        write_worksheet(excel_writer, get_time_series_data("%H"), "時間帯別のつぶやき数")

        # つぶやきの内容を書き込み
        df = get_tweet_text_data()
        write_worksheet(excel_writer, df, "全てのつぶやき")

        # YAMLファイルから検索キーワードのリストを読み取り、OR検索用の文字列を生成する。
        with open("more_search_keywords.yml", "r") as file:
            keywords = yaml.load(file)

        # つぶやきの内容を書き込み（さらにキーワードで絞込）
        [write_worksheet(excel_writer, df[(df["text"].str.contains(keyword))].reset_index(drop=True),
                         "「{0}」を含むつぶやき".format(keyword))
         for keyword in keywords]

        excel_writer.save()
        print("end a creating {0}".format(excel_file_path))

    except Exception as e:
        print(str(e))
        logger.exception(str(e))
        raise

if __name__ == '__main__':
    create_excel_workbook("data/Twitter分析_{0}.xlsx".format(datetime.now().strftime("%Y%m%d")))

