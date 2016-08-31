#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import MeCab
import pymongo
import config as config
from gensim.models import word2vec
from shared.datetime_extentions import *
import shared.text_utility as util


# word2vecを使ったサンプルです。

def analyze(start_datetime: datetime, end_datetime: datetime):
    tagger = MeCab.Tagger('-Owakati -d ' + config.MECAB_USER_DICT)
    data_file = os.path.abspath('../out/wakati.txt')

    try:
        # 分かち書きを行い、テキストファイルに保存しておく。
        with open(data_file, 'w') as f:
            client = pymongo.MongoClient(config.HOST, config.PORT)
            tweets = client[config.DB_NAME][config.COLLECTION_NAME]
            cond = {'retweeted_status': {'$eq': None}, 'spam': {'$eq': None},
                    'created_datetime': {'$gte': start_datetime, '$lte': end_datetime}}

            for tweet in tweets.find(cond, {'id': 1, 'text': 1}):
                f.write(tagger.parse(util.get_text_eliminated_some_pattern_words(tweet["text"])))

        sentences = word2vec.Text8Corpus(data_file)

        # sentences : 分かち書き済の文字列
        # size      : 出力するベクトルの次元数
        # min_count : この数値よりも登場回数が少ない単語は無視される
        model = word2vec.Word2Vec(sentences, size=200, min_count=1)

        def show(positive, negative=None, n=10):
            if negative is None:
                negative = []

            print('--------------------------------------')
            print('positive = ', positive, 'negative = ', negative)
            print('--------------------------------------')

            # 学習済みモデルからcos距離が最も近い単語を抽出
            result = model.most_similar(positive=positive, negative=negative, topn=n)
            for r in result:
                print(r[0], r[1])

        show(['印刷'])
        show(['写真'])
        show(['面倒'])

        """ 出力例
        --------------------------------------
        positive =  ['印刷'] negative =  []
        --------------------------------------
        プリント 0.9551246166229248
        刷り 0.8528412580490112
        マンモス 0.8433887958526611
        書類作成 0.8288816213607788
        薬局 0.8165526390075684
        見返し 0.7979863286018372
        成功 0.794916033744812
        ブレ 0.7879878282546997
        非公開 0.7873853445053101
        ざちよの 0.7865146994590759
        --------------------------------------
        positive =  ['写真'] negative =  []
        --------------------------------------
        文書 0.938888430595398
        ネット 0.9246827363967896
        振込 0.9013392925262451
        冊子 0.8994526267051697
        ブロマイド 0.8911961317062378
        手軽 0.889725387096405
        画像 0.8831754922866821
        ドラム 0.8829593062400818
        上限 0.8828651905059814
        紙 0.8729526400566101
        --------------------------------------
        positive =  ['面倒'] negative =  []
        --------------------------------------
        フォルダー 0.9385091066360474
        そもそも 0.9272475242614746
        ティア 0.9226386547088623
        下ろす 0.9169464111328125
        プリンター 0.9149339199066162
        CMYK 0.9128730297088623
        無い 0.9079633951187134
        そっち 0.9069767594337463
        紙 0.9065827131271362
        使う 0.9026138186454773
        """

    finally:
        os.remove(data_file)


if __name__ == '__main__':
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    ten_days_ago = tomorrow - timedelta(days=10)
    analyze(start_datetime=ten_days_ago, end_datetime=today)
