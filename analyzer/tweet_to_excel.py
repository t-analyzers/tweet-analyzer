import pandas as pd
import yaml
from pandas import DataFrame

import analyzer.time_series as time_series
from analyzer.date_ext import *
from analyzer.db import *
from analyzer.logger import Log

# coding=utf-8
# write code...

log = Log('excel')


def get_tweet_text_data(condition) -> DataFrame:
    """
    つぶやきの内容をMongoDBから取得する
    :param condition: 検索の絞り込み条件（Dictionary）
    :return: DataFrame
    """
    tweet_collection = connect_tweet_collection()
    date_format = '%Y/%m/%d %a %H:%M:%S'
    results = [
        {'created_datetime': date_to_japan_time(tweet['created_datetime']).strftime(date_format),
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
    log.info(msg)


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
        write_worksheet(excel_writer, time_series.get_time_series_data(distance, '%Y %m/%d %H %a'), '1時間ごとのつぶやき数')
        # 日ごとのつぶやき数
        write_worksheet(excel_writer, time_series.get_time_series_data(distance, '%Y %m/%d'), '日ごとのつぶやき数')
        # 時間帯別のつぶやき数
        write_worksheet(excel_writer, time_series.get_time_series_data(distance, '%H'), '時間帯別のつぶやき数')

        # つぶやきの内容を書き込み
        df = get_tweet_text_data({'retweeted_status': {'$eq': None},
                                  'created_datetime': {'$gte': start_time, '$lte': end_time}})
        write_worksheet(excel_writer,
                        df.sort_values(by='created_datetime', ascending=False).reset_index(drop=True), '全てのつぶやき')

        # YAMLファイルから絞り込み用キーワードのリストを読み取る。
        with open('conf/more_search_keywords.yml', 'r', encoding='utf-8') as file:
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
        log.exception(str(e))
        raise

if __name__ == '__main__':
    today = datetime.today()
    file_path = 'excel/Twitter分析_{0}.xlsx'.format(datetime.now().strftime('%Y%m%d'))
    create_excel_workbook(file_path, today - timedelta(days=7), today)
