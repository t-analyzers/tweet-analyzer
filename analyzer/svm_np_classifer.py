# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 15:29:23 2016

@author: hitoshi
"""
import pymongo
from shared.datetime_extentions import *
import config_svm_np
import datetime
from pytz import timezone
import json
import os.path
from os.path import join, relpath
import copy

import urllib.request, urllib.parse
import shared.text_utility as util

#形態素解析のライブラリ
import MeCab

from sklearn import svm
from sklearn.grid_search import GridSearchCV
from sklearn.feature_extraction.text import CountVectorizer

import pandas as pd

def wakati(text):
    tagger = MeCab.Tagger()
    tagger.parse('')
    node = tagger.parseToNode(text)
    word_list = []
    while node:
        pos = node.feature.split(",")[0]
        if pos in ["名詞", "動詞", "形容詞"]:
            lemma = node.feature.split(",")[6]
            if lemma == u"*":
                lemma = node.surface
            word_list.append(lemma)
        node = node.next
#    return u" ".join(word_list[1:-1]) #[1:-1]を入れると最初と最後の単語が除かれてしまうため外した。
    return u" ".join(word_list)

#connection mongoDB to get sample-tweets
client = pymongo.MongoClient(config_svm_np.HOST, config_svm_np.PORT)
input_collection = client[config_svm_np.DB_NAME][config_svm_np.INPUT_COLLECTION_NAME]
sample_collection = client[config_svm_np.DB_NAME][config_svm_np.SAMPLE_COLLECTION_NAME]

tweets = []
tweets_wakati = []
tweets_label = []

print("[INFO] 分かち書き")
for tweet in sample_collection.find({},{'text': 1, 'additional_info': 1}):
    # negaposi_int = 1 or -1のデータのみ教師データとして使用する
    if tweet['additional_info']['metadata_api']['negaposi_int'] != 0:
        tweet['wakati'] = wakati(util.get_text_eliminated_some_pattern_words(tweet['text']))
        tweet['label'] = tweet['additional_info']['metadata_api']['negaposi_int']
        tweets.append(tweet)
        tweets_wakati.append(tweet['wakati'])
        tweets_label.append(tweet['label'])
    
print("[INFO] 素性ベクトル作成")
count_vectorizer = CountVectorizer()
#feature_vectors = count_vectorizer.fit_transform(tweets['wakati'])
feature_vectors = count_vectorizer.fit_transform(tweets_wakati)
vocabulary = count_vectorizer.get_feature_names()

### SVM による学習
print("[INFO] SVM (グリッドサーチ)")
svm_tuned_parameters = [
    {
        'kernel': ['rbf'],
        'gamma': [2**n for n in range(-15, 3)],
        'C': [2**n for n in range(-5, 15)]
    }
]
gscv = GridSearchCV(
    svm.SVC(),
    svm_tuned_parameters,
    cv=5,      # クロスバリデーションの分割数
    n_jobs=1,  # 並列スレッド数
    verbose=3  # 途中結果の出力レベル 0 だと出力しない
)
#gscv.fit(feature_vectors, list(tweets['label']))
gscv.fit(feature_vectors, tweets_label)
svm_model = gscv.best_estimator_  # 最も精度の良かったモデル
print(svm_model)

### SVM による分類
print("[INFO] SVM (分類)")
sample_text = pd.Series([
    u"無免許運転をネット中継 逮捕  - Y!ニュース news.yahoo.co.jp/pickup/...",
    u"田舎特有のいじめが原因かな……複数殺人および未遂って尋常じゃない恨みだろ | Reading:兵庫県洲本市で男女５人刺される ３人死亡　NHKニュース",
    u"BABYMETAL、CDショップ大賞おめでとうございます。これからも沢山の方がBABYMETALに触れる事でしょうね。音楽ってこんなにも楽しいって教えられましたもん。 ",
    u"タカ丸さんかわいいな～",
    
    u"チェキ風ネットプリント作ったものの解像度間違えてしまった",
    u"ネットプリントおみくじやるとしても３２人分アップするのめんどくさいな",
    u"ここにきて重大な事が発覚\nネットプリントのやり方しらねぇ！",
    u"ネットプリントまたやるか悩むけどおそらく需要ないんじゃ",
    
    u"ネットプリント初めてしてみた！楽しい。",
    u"みそさんのイラスト好きすぎてネットプリントで欲しい、スケジュール帳に挟みたい",
    u"こんばんは！やますけさんのイラスト印刷してみました！色がとても綺麗に出ていましたよ～調整など諸々大変だったのではないでしょうか",
    u"フォロー外から、失礼します！ネットプリントさせていただきました！デザインがオシャレで素敵です。プリントすると少し濃い目になっちゃうんですね(O_O)これはこれで好きですが。",
    u"のんちゃんありがとう。ネットプリント用に編集してよかったー！綺麗に印刷出来てて安心"
])
split_sample_text = sample_text.apply(wakati)
count_vectorizer = CountVectorizer(
    vocabulary=vocabulary # 学習時の vocabulary を指定する
)
feature_vectors = count_vectorizer.fit_transform(split_sample_text)

print(svm_model.predict(feature_vectors))