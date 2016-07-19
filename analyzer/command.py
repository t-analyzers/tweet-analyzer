import os
from _datetime import *

import click

from archiver import TweetArchiver
from report_creator import ReportCreator
from spam_detector import SpamDetector
from pn_dict_scorer import PnDictScorer


# coding=utf-8
# write code...


@click.group()
def cmd():
    pass


@cmd.command('a', short_help=': save the tweet to MongoDB.')
def archive_tweets():
    TweetArchiver().archive()

    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    # Twitter APIでは最大7-10日間分くらい検索可能なので、それよりも広めな14日間の範囲で検索する。
    two_weeks_ago = tomorrow - timedelta(days=14)
    SpamDetector().divide_spam_tweet(start_datetime=two_weeks_ago, end_datetime=tomorrow, limit_tweet_count=60)

    PnDictScorer().update_negaposi(start_datetime=two_weeks_ago, end_datetime=tomorrow)


@cmd.command('e', short_help=': create the excel format of the report.')
@click.option('--file',
              default=os.path.abspath('../out/Twitter分析_{0}.xlsx'.format(datetime.now().strftime('%Y%m%d'))),
              help='Excel file absolute path.')
def create_excel_report(file):
    print('Excel形式のレポートを{0}に出力します。'.format(file))
    today = datetime.today()
    ReportCreator().create_excel(file, start_time=today - timedelta(days=7), end_time=today)


def main():
    cmd()

if __name__ == '__main__':
    main()
