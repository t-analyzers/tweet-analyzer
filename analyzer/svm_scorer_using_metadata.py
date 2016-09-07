# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 15:29:23 2016

@author: hitoshi
"""
import pymongo
import config_svm_np
import datetime
from pytz import timezone
#import json
#import os.path
#from os.path import join, relpath
#import copy

#import urllib.request, urllib.parse
#from shared.datetime_extentions import dutil
import shared.text_utility as util

#形態素解析のライブラリ
import MeCab

from sklearn import svm
from sklearn.grid_search import GridSearchCV
from sklearn.feature_extraction.text import CountVectorizer

import pandas as pd


class SvmScorerUseMetadataLearingData():

    #connection mongoDB to get sample-tweets
    client = pymongo.MongoClient(config_svm_np.HOST, config_svm_np.PORT)
    
    #SVMでの学習結果を格納するグローバル変数
    svm_models_dict = {}
        
    def __int__(self):
        super().__init__()


    def supervised_learning(self):
        '''
        SVMによる教師あり学習を行い、判定を行うためのvocablary, svm_modelをグローバル変数に格納し、返す。
        教師データはcreat_learning_data_by_metadata.pyでMongoDBに取り込んだデータを使用する。
        
        実験的に2値判定(ポジorNotポジ、ネガorNotネガ)と3値判定（ネガ、ポジ、どちらでもない）を行う。
        :return:  {"vocablary":{"p": 語彙リスト（ポジ）, "n": 語彙リスト（ネガ）, "a": 語彙リスト（ALL）}, 
                   "svm_model":{"p": SVMモデル(ポジ), "n": SVMモデル(ネガ), "n": SVMモデル(ALL)}}
        '''
        
        # Positive or NOT Positive(2値)
        tweets_wakati_p = []
        tweets_label_p = []
        
        #Negative or NOT Negative(2値)
        tweets_wakati_n = []
        tweets_label_n = []
    
        #ネガポジ(3値)
        tweets_wakati_a = []
        tweets_label_a = []
        
        sample_collection = self.client[config_svm_np.DB_NAME][config_svm_np.SAMPLE_COLLECTION_NAME]
        
        print("[INFO] 分かち書き")
        for tweet in sample_collection.find({},{'text': 1, 'additional_info': 1}):
            negaposi_int = tweet['additional_info']['metadata_api']['negaposi_int']
            
            # negaposi_int = 1 or 0のデータをポジティブ判定の教師データとして使用する
            if negaposi_int >= 0:
                tweet['wakati'] = self._wakati(util.get_text_eliminated_some_pattern_words(tweet['text']))
                tweet['label'] = negaposi_int
                tweets_wakati_p.append(tweet['wakati'])
                tweets_label_p.append(tweet['label'])
        
            # negaposi_int = -1 or 0のデータをネガティブ判定の教師データとして使用する
            if negaposi_int <= 0:
                tweet['wakati'] = self._wakati(util.get_text_eliminated_some_pattern_words(tweet['text']))
                tweet['label'] = negaposi_int
                tweets_wakati_n.append(tweet['wakati'])
                tweets_label_n.append(tweet['label'])
    
            tweets_wakati_a.append(tweet['wakati'])
            tweets_label_a.append(tweet['label'])
            
        print("[INFO] 素性ベクトル作成")
        count_vectorizer = CountVectorizer()
        feature_vectors_p = count_vectorizer.fit_transform(tweets_wakati_p)
        vocabulary_p = count_vectorizer.get_feature_names()
        
        feature_vectors_n = count_vectorizer.fit_transform(tweets_wakati_n)
        vocabulary_n = count_vectorizer.get_feature_names()
    
        feature_vectors_a = count_vectorizer.fit_transform(tweets_wakati_a)
        vocabulary_a = count_vectorizer.get_feature_names()
        
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
            n_jobs=2,  # 並列スレッド数
            verbose=3  # 途中結果の出力レベル 0 だと出力しない
        )
        #ポジティブ判定
        gscv.fit(feature_vectors_p, tweets_label_p)
        svm_model_p = gscv.best_estimator_  # 最も精度の良かったモデル
        #print(svm_model_p)
        
        #ネガティブ判定
        gscv.fit(feature_vectors_n, tweets_label_n)
        svm_model_n = gscv.best_estimator_  # 最も精度の良かったモデル
        #print(svm_model_n)
        
        #ネガポジ判定
        gscv.fit(feature_vectors_a, tweets_label_a)
        svm_model_a = gscv.best_estimator_  # 最も精度の良かったモデル
        
        #3つのモデルをグローバル変数に格納。
        self.svm_models_dict = {
                "vocabulary":{"p": vocabulary_p, "n": vocabulary_n, "a": vocabulary_a}, 
                "svm_model":{"p": svm_model_p, "n": svm_model_n, "a": svm_model_a}
                }      
        
        return self.svm_models_dict
    
    def svm_classifer(self, text_list):
        '''
        supervised_learning_with_svmの結果を使って文章の判定を実行。
        引数の文章リストが空の場合、サンプルの文章の判定を行う。
        実験的に2値判定(ポジorNotポジ、ネガorNotネガ)と3値判定（ネガ、ポジ、どちらでもない）のモデルを使用する。
        :return: 判定結果リスト(ポジ: 1、ネガ: -1、どちらでもない: 0)　※2値判定の合成結果
        '''
        vocabulary_p = self.svm_models_dict["vocabulary"]["p"]
        vocabulary_n = self.svm_models_dict["vocabulary"]["n"]
        vocabulary_a = self.svm_models_dict["vocabulary"]["a"]
        svm_model_p = self.svm_models_dict["svm_model"]["p"]
        svm_model_n = self.svm_models_dict["svm_model"]["n"]
        svm_model_a = self.svm_models_dict["svm_model"]["a"]
        
        ### SVM による分類
        print("[INFO] SVM (分類)")
        texts = {}
        is_sample = False
        if len(text_list) != 0:
            texts = pd.Series(text_list)
        else:
            is_sample = True
            texts = pd.Series([
                u"ﾈｯﾄﾌﾟﾘﾝﾄ用にお祭りものかこうかと https://t.co/zjKua2yXGu",
                u"暇だから私もネットプリントやろうかな( ˘ω˘ )",
                u"ネットプリント、何か皆やってね？",
                u"ペーパーはそのうちPixivにのっけますし、ちょっとやってみたかったのでネットプリントにも投げてみます。",
                u"ネットプリントやり方検索検索ゥ！！",
                
                u"チェキ風ネットプリント作ったものの解像度間違えてしまった",
                u"ネットプリントおみくじやるとしても３２人分アップするのめんどくさいな",
                u"ここにきて重大な事が発覚\nネットプリントのやり方しらねぇ！",
                u"ネットプリントまたやるか悩むけどおそらく需要ないんじゃ",
                u"ネットプリント二次創作はマズイのかしら…やめとこうかな",
                
                u"ネットプリント初めてしてみた！楽しい。",
                u"みそさんのイラスト好きすぎてネットプリントで欲しい、スケジュール帳に挟みたい",
                u"こんばんは！やますけさんのイラスト印刷してみました！色がとても綺麗に出ていましたよ～調整など諸々大変だったのではないでしょうか",
                u"フォロー外から、失礼します！ネットプリントさせていただきました！デザインがオシャレで素敵です。プリントすると少し濃い目になっちゃうんですね(O_O)これはこれで好きですが。",
                u"のんちゃんありがとう。ネットプリント用に編集してよかったー！綺麗に印刷出来てて安心"
            ])
            
        split_texts = texts.apply(self._wakati)
        
        #ポジティブ判定(2値)
        count_vectorizer = CountVectorizer(
            vocabulary=vocabulary_p # 学習時の vocabulary を指定する
        )
        feature_vectors = count_vectorizer.fit_transform(split_texts)
        positive_class = svm_model_p.predict(feature_vectors)
        print("### POSITIVE: 1     NOT POSITIVE: 0")
        if is_sample == True: print("期待値：[0,0,0,0,0,0,0,0,0,0,1,1,1,1,1]")
        print(positive_class)
        
        #ネガティブ判定(2値)
        count_vectorizer = CountVectorizer(
            vocabulary=vocabulary_n # 学習時の vocabulary を指定する
        )
        feature_vectors = count_vectorizer.fit_transform(split_texts)
        negative_class = svm_model_n.predict(feature_vectors)
        print("###NEGATIVE: -1     NOT NEGATIVE: 0")
        if is_sample == True: print("期待値：[0,0,0,0,0,-1,-1,-1,-1,-1,0,0,0,0,0]")
        print(negative_class)
        
        #上記ポジティブ判定とネガティブ判定を合成する
        negaposi_class = []
        for i in range(0,len(positive_class)):
            negaposi_class.append(negative_class[i] + positive_class[i])
            
        print("### 合計結果 POSITIVE: 1  NEGATIVE: -1  NUTORAL: 0")
        if is_sample == True: print("期待値：[0,0,0,0,0,-1,-1,-1,-1,-1,1,1,1,1,1]")
        print(negaposi_class)
    
        #ネガポジ判定(3値)用のモデルで判定する
        count_vectorizer = CountVectorizer(
            vocabulary=vocabulary_a # 学習時の vocabulary を指定する
        )
        feature_vectors = count_vectorizer.fit_transform(split_texts)
        negaposi_all_class = svm_model_a.predict(feature_vectors)
        print("### ネガポジALLのモデル使用")
        print("###POSITIVE: 1   NEGATIVE: -1  NUTRAL: 0")
        if is_sample == True: print("期待値：[0,0,0,0,0,-1,-1,-1,-1,-1,1,1,1,1,1]")
        print(negaposi_all_class)
        
        return negaposi_class
        
    def update_negaposi(self, start_datetime: datetime, end_datetime: datetime):
        '''
        supervised_learning_with_svmの結果を使って文章の判定を実行。
        3値判定（ネガ、ポジ、どちらでもない）のモデルを使用する。
        '''

        search_condition = {'retweeted_status': {'$eq': None}, 'spam': {'$eq': None},
                            'created_datetime': {'$gte': start_datetime, '$lte': end_datetime}}
        
        tweets = self.client[config_svm_np.DB_NAME][config_svm_np.COLLECTION_NAME]
        for tweet in tweets.find(search_condition, {'text': 1}):
            score = self.svm_classifer([tweet["text"]])[0] #型: numpy.int64
            print(tweet["text"])
            print("スコア：" + str(score))
            tweets.update_one({'_id': tweet['_id']}, {'$set': {'negaposi': int(score)}})  #scoreの型を明示的にintに変換。型変換しないとエラーになる。

    def _wakati(self, text):
        '''
        文字列を形態素解析し、「名詞」「動詞」「形容詞」を抽出して半角スペースで連結して返す
        :return: 「名詞」「動詞」「形容詞」を半角スペースで連結した文字列
        '''
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

if __name__ == "__main__" :
    
    SvmScorer = SvmScorerUseMetadataLearingData()
    #教師データから学習
    svm_models_dict = SvmScorer.supervised_learning()
    
    # tweetにネガポジ判定結果を付与(update)  7日分遡って更新する
    d = datetime.datetime.now()
    date = datetime.datetime(d.year,d.month,d.day,0,0,0,0,timezone('Asia/Tokyo'))
    start_datetime = date - datetime.timedelta(days=7)
    date = datetime.datetime(d.year,d.month,d.day,23,59,59,999999,timezone('Asia/Tokyo'))
    end_datetime = date - datetime.timedelta(days=0)
    
    SvmScorer.update_negaposi(start_datetime,end_datetime)
    
    #学習データの顕正
    SvmScorer.svm_classifer([])
    