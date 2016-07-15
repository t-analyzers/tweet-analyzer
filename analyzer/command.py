import os
from _datetime import *

import click

from archiver import TweetArchiver
from report_creator import ReportCreator
from spam_detector import SpamDetector
from negaposi import MecabEvaluator


# coding=utf-8
# write code...


@click.group()
def cmd():
    pass


@cmd.command('a', short_help=': save the tweet to MongoDB.')
def archive_tweets():
    print('ツィートをMongoDBに保存します。')
    TweetArchiver().archive()

    print('スパムツィートを検索します。')
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    # Twitter APIでは最大7-10日間分くらい検索可能なので、それよりも広めな14日間の範囲で検索する。
    two_weeks_ago = tomorrow - timedelta(days=14)
    SpamDetector().divide_spam_tweet(two_weeks_ago, tomorrow, 60)

    print("ネガポジスコアの算出開始")
    MecabEvaluator().set_negaposi_score(two_weeks_ago, tomorrow)
    print("ネガポジスコアの算出完了")


@cmd.command('e', short_help=': create the excel format of the report.')
@click.option('--file',
              default=os.path.abspath('../out/Twitter分析_{0}.xlsx'.format(datetime.now().strftime('%Y%m%d'))),
              help='Excel file absolute path.')
def create_excel_report(file):
    print('Excel形式のレポートを{0}nに出力します。'.format(file))
    today = datetime.today()
    ReportCreator().create_excel(file, today - timedelta(days=7), today)


def main():
    cmd()

if __name__ == '__main__':
    main()
