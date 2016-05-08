from collections import defaultdict
import pandas as pd
from pandas import DataFrame, Series
import config
import pymongo
import date_utilities
from logger import Logger
import yaml
from _datetime import *

# coding=utf-8
# write code...

logger = Logger('excel')
client = pymongo.MongoClient(config.HOST, config.PORT)
tweet_collection = client[config.DB_NAME][config.COLLECTION_NAME]


def get_time_series_data(condition, date_format) -> DataFrame:
    """
    日付フォーマットに合致するつぶやき数をDataFrameにまとめて返す
    :param condition: 検索の絞り込み条件（Dictionary）
    :param date_format: 日付フォーマット、指定されたフォーマットごとにつぶやき数を計算する
    :return: DataFrame
    """
    all_date_dict = defaultdict(int)
    ret_date_dict = defaultdict(int)
    norm_date_dict = defaultdict(int)
    spam_dict = defaultdict(int)
    not_spam_all_dict = defaultdict(int)
    not_spam_norm_dict = defaultdict(int)
    not_spam_ret_dict = defaultdict(int)

    for tweet in tweet_collection.find(condition, {'_id': 1, 'created_datetime': 1, 'retweeted_status': 1, 'spam': 1}):
        str_date = date_utilities.date_to_japan_time(tweet['created_datetime']).strftime(date_format)
        all_date_dict[str_date] += 1

        # spamの除去
        if ('spam' in tweet) and (tweet['spam'] == True):
            spam_dict[str_date] += 1
            not_spam_all_dict[str_date] += 0
        else:
            spam_dict[str_date] += 0
            not_spam_all_dict[str_date] += 1
            # spamでないもののRetweet数のカウント
            if 'retweeted_status' not in tweet:
                not_spam_ret_dict[str_date] += 0
                not_spam_norm_dict[str_date] += 1
            elif tweet['retweeted_status'] is not None:
                not_spam_ret_dict[str_date] += 1
                not_spam_norm_dict[str_date] += 0
            else:
                not_spam_ret_dict[str_date] += 0
                not_spam_norm_dict[str_date] += 1

        if 'retweeted_status' not in tweet:
            ret_date_dict[str_date] += 0
            norm_date_dict[str_date] += 1
        elif tweet['retweeted_status'] is not None:
            ret_date_dict[str_date] += 1
            norm_date_dict[str_date] += 0
        else:
            ret_date_dict[str_date] += 0
            norm_date_dict[str_date] += 1

    df = pd.concat([Series(all_date_dict), Series(norm_date_dict), Series(ret_date_dict), Series(spam_dict),
                    Series(not_spam_all_dict), Series(not_spam_norm_dict), Series(not_spam_ret_dict)], axis=1)
    df.columns = ['#ALL', '#NotRT', '#RT', '#spam', '#ALL(exclude spam)', '#NotRT(exclude spam)', '#RT(exclude spam)']
    return df


def get_tweet_text_data(condition) -> DataFrame:
    """
    つぶやきの内容をMongoDBから取得する
    :param condition: 検索の絞り込み条件（Dictionary）
    :return: DataFrame
    """
    date_format = '%Y/%m/%d %a %H:%M:%S'
    results = [
        {'created_datetime': date_utilities.date_to_japan_time(tweet['created_datetime']).strftime(date_format),
         'retweet_count': tweet['retweet_count'], 'id': tweet['id'],
         'user.screen_name': tweet['user']['screen_name'], 'text': tweet['text']}
        for tweet in tweet_collection.find(condition,
                                           {'created_datetime': 1, 'retweet_count': 1, 'id': 1, 'user': 1, 'text': 1})]

    return DataFrame(results, columns=['created_datetime', 'retweet_count', 'id', 'user.screen_name', 'text'])


def write_worksheet(excel_writer, data_frame, sheet_name):
    """
    ワークシートにDataFrameの内容を書き込む
    :param excel_writer: ExcelWriterオブジェクト
    :param data_frame: 書き込み対象のDataFrameオブジェクト
    :param sheet_name: ワークシートの名前
    :return: なし
    """
    data_frame.to_excel(excel_writer, sheet_name=sheet_name)
    msg = 'wrote worksheet {0}'.format(sheet_name)
    print(msg)
    logger.info(msg)


def create_excel_workbook(excel_file_path, start_time, end_time):
    """
    Excellにつぶやきの内容を書き込む
    :param excel_file_path: 出力先のファイルパス
    :param start_time: 検索対象とする開始時刻
    :param end_time: 検索対象とする終了時刻
    :return: なし
    """
    try:
        print('start a creating {0}'.format(excel_file_path))
        # Excelを作成するためのオブジェクトを初期化
        excel_writer = pd.ExcelWriter(excel_file_path, engine='xlsxwriter')

        # デフォルトの検索条件、「start_time - end_time」の間のつぶやきを検索対象とする。
        distance = {'created_datetime': {'$gte': start_time, '$lte': end_time}}
        # 1時間ごとのつぶやき数
        write_worksheet(excel_writer, get_time_series_data(distance, '%Y %m/%d %H %a'), '1時間ごとのつぶやき数')
        # 日ごとのつぶやき数
        write_worksheet(excel_writer, get_time_series_data(distance, '%Y %m/%d'), '日ごとのつぶやき数')
        # 時間帯別のつぶやき数
        write_worksheet(excel_writer, get_time_series_data(distance, '%H'), '時間帯別のつぶやき数')

        # つぶやきの内容を書き込み
        df = get_tweet_text_data({'retweeted_status': {'$eq': None},
                                  'created_datetime': {'$gte': start_time, '$lte': end_time}})
        write_worksheet(excel_writer,
                        df.sort_values(by='created_datetime', ascending=False).reset_index(drop=True), '全てのつぶやき')

        # YAMLファイルから絞り込み用キーワードのリストを読み取る。
        with open('more_search_keywords.yml', 'r', encoding='utf-8') as file:
            keywords = yaml.load(file)

        # つぶやきの内容を書き込み（さらにキーワードで絞込）
        [write_worksheet(excel_writer,
                         df[(df['text'].str.contains(keyword))]
                         .sort_values(by='created_datetime', ascending=False)
                         .reset_index(drop=True), '「{0}」を含むつぶやき'.format(keyword)) for keyword in keywords]

        spam_df = get_tweet_text_data({'spam': {'$eq': True},
                                       'created_datetime': {'$gte': start_time, '$lte': end_time}})

        write_worksheet(excel_writer,
                        spam_df.sort_values(by='created_datetime', ascending=False).reset_index(drop=True), 'spam')

        excel_writer.save()
        print('end a creating {0}'.format(excel_file_path))

    except Exception as e:
        print(str(e))
        logger.exception(str(e))
        raise


if __name__ == '__main__':
    now = datetime.now()
    file_path = 'data/Twitter分析_{0}.xlsx'.format(date_utilities.datetime.now().strftime('%Y%m%d'))
    create_excel_workbook(file_path, now - timedelta(days=7), now)
