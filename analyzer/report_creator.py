import datetime

import pandas as pd
import yaml

from shared.decorators import trace
from shared.log import Log
from sample_analyzer import SampleAnalyzer
from tweet_counter import TweetCounter

# coding=utf-8
# write code...


class ReportCreator(object):
    """
    レポートを作成するクラス
    """

    def __init__(self):
        self.log = Log(self.__class__.__name__)

    @trace()
    def create_excel(self, excel_file_path: str, start_time: datetime, end_time: datetime):
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
            condition = {'created_datetime': {'$gte': start_time, '$lte': end_time}}

            tweet_counter = TweetCounter()

            # 1時間ごとのつぶやき数
            self._write_worksheet(excel_writer,
                                  tweet_counter.get_time_series_data(condition, '%Y %m/%d %H %a'),
                                  '1時間ごとのつぶやき数')
            # 日ごとのつぶやき数
            self._write_worksheet(excel_writer,
                                  tweet_counter.get_time_series_data(condition, '%Y %m/%d'),
                                  '日ごとのつぶやき数')

            # 時間帯別のつぶやき数
            self._write_worksheet(excel_writer,
                                  tweet_counter.get_time_series_data(condition, '%H'),
                                  '時間帯別のつぶやき数')

            sample_analyzer = SampleAnalyzer()

            # つぶやきの内容を書き込み
            df = sample_analyzer.get_text_data({'retweeted_status': {'$eq': None},
                                                'created_datetime': {'$gte': start_time, '$lte': end_time}})

            self._write_worksheet(excel_writer, df, '全てのつぶやき')

            # YAMLファイルから絞り込み用キーワードのリストを読み取る。
            with open('conf/more_search_keywords.yml', 'r', encoding='utf-8') as file:
                keywords = yaml.load(file)

            # つぶやきの内容を書き込み（さらにキーワードで絞込）
            [self._write_worksheet(excel_writer,
                                   df[(df['text'].str.contains(keyword))].
                                   sort_values(by='created_datetime', ascending=False).reset_index(drop=True),
                                   '「{0}」を含むつぶやき'.format(keyword)) for keyword in keywords]

            spam_df = sample_analyzer.get_text_data({'spam': {'$eq': True},
                                                     'created_datetime': {'$gte': start_time, '$lte': end_time}})

            self._write_worksheet(excel_writer, spam_df, 'spam')

            excel_writer.save()
            print('end a creating {0}'.format(excel_file_path))

        except Exception as e:
            print(str(e))
            self.log.exception(str(e))
            raise

    def _write_worksheet(self, excel_writer, data_frame, sheet_name):
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
        self.log.info(msg)
