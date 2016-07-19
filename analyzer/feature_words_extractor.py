# -*- coding: utf-8 -*-
"""
archve.pyで取り込んだtweetsを分析する。
・分析内容：
　日にちごとの頻出単語トップXX
  XXはconfig_feature_words.pyで設定可能。
 
 出力ファイル：
   - feature_words_YYYYMMDD-YYYYMMDD.json
       [{"date": , "tweet_count":, "retweet_count":,"feature_words":[...]},...] ※dateでソート
   - tweets_YYYYMMDD.json x 指定期間日数
       [{'created_datetime': ,'retweet_count': , 'id': , user.screen_name': , 'text':, 'media_urls':, 'nouns': ,'PrintID' }, ...] ※created_datetimeでソート
@author: hitoshi
"""
from collections import defaultdict
import pymongo
#import date_utilities
from shared.datetime_extentions import *
import config_feature_words
import datetime
from pytz import timezone
import json
import os.path

#形態素解析のライブラリ
import MeCab
#TF-IDFフィルタのクラス
from sklearn.feature_extraction.text import TfidfVectorizer

#正規表現処理用のクラス
import re

client = pymongo.MongoClient(config_feature_words.HOST, config_feature_words.PORT)
tweet_collection = client[config_feature_words.DB_NAME][config_feature_words.COLLECTION_NAME]

#分析するデータの日数
ANALYZE_DAYS =config_feature_words.ANALYZE_DAYS
#抽出単語数
EXTRACT_FEATURE_WORDS_MAX = config_feature_words.EXTRACT_FEATURE_WORDS_MAX
#TF-IDFパラメータ：　除外する合計出現回数
TFIDF_EXCLUDE_APPEARANCE = config_feature_words.TFIDF_EXCLUDE_APPEARANCE


def get_feature_words_from_tweets_text(condition, date_format):
    """
    日付フォーマットに合致するつぶやきの頻出名詞をJSON形式で返す
    :param condition: 検索の絞り込み条件（Dictionary）
    :param date_format: 日付フォーマット、指定されたフォーマットごとにつぶやき数を計算する
    :return: JSON [{},...]
    """
    
    tweets_count_dict = defaultdict(int) #集計時間単位（以下、わかりやすくするために「日別」とする）のtweet件数
    retweets_count_dict = defaultdict(int)
    nouns_dict = defaultdict(str) #「日別」のtweet textの名詞を連結した文字列
    words_dict = defaultdict(str)
    
    target_time_units =[] #date_formatで指定した年月日時文字列。例）date_format='%Y%m%d'の場合は'2016/06/01'のような日にちの配列になる。
    target_time_unit_nouns =[] #date_formatで指定した年月日時ごとのtweetに含まれる名詞を連結した文字列
    
    #tweetsの読み込み（mongoDBからのfind時のsortはメモリ不足でエラーになるため、ファイル出力前にこのプログラムでソートする）
    for tweet in tweet_collection.find(condition, {'_id': 1, 'created_datetime': 1,'retweeted_status': 1, 'text': 1}):
        #str_date = date_utilities.date_to_japan_time(tweet['created_datetime']).strftime(date_format)
        str_date = date_to_japan_time(tweet['created_datetime']).strftime(date_format)
        
        #初めて処理する日付の場合はtarget_time_unitsに格納する
        if (str_date in target_time_units) == False :
            target_time_units.append(str_date)
            
        #その日の件数をカウントアップする
        tweets_count_dict[str_date] += 1 
        
        #そのツイートがretweetの場合はカウントアップする
        if 'retweeted_status' in tweet:
            retweets_count_dict[str_date] += 1
        
        #形態素解析で名詞を抽出して文字列として連結する
        nouns_dict[str_date] += " " + split_text_only_noun(get_text_eliminated_some_pattern_words(tweet['text']))

    #日付リストをソート
    target_time_units.sort()
    
    #TF-IDF用にnouns_dictからtarget_time_unit_nounsへ格納する。
    for i in range(0, len(target_time_units)) :
        target_time_unit_nouns.append(nouns_dict[target_time_units[i]])
    
    # TF-IDF 計算
    # TFIDF_EXCLUDE_APPEARANCE日以上出現した単語は除外
    tfidf_vectorizer = TfidfVectorizer(
        use_idf=True,
        lowercase=False,
        max_df=TFIDF_EXCLUDE_APPEARANCE
    )
    tfidf_matrix = tfidf_vectorizer.fit_transform(target_time_unit_nouns)
    # index 順の単語のリスト
    terms = tfidf_vectorizer.get_feature_names()
    # TF-IDF 行列 (numpy の ndarray 形式)
    tfidfs = tfidf_matrix.toarray()
    
    # 結果の出力
    for i in range(0, len(target_time_units)) :
        words_dict[target_time_units[i]] = []
        for x in  extract_feature_words(terms, tfidfs, i, EXTRACT_FEATURE_WORDS_MAX):
            words_dict[target_time_units[i]].append(x)

    results_list =[]
    for i in range(0, len(target_time_units)) :
        result = {"date": target_time_units[i], "tweets_count": tweets_count_dict[target_time_units[i]], "retweets_count": retweets_count_dict[target_time_units[i]], "feature_words": words_dict[target_time_units[i]]}
        results_list.append(result)
    
    print(results_list)
    #dateで降順ソートする
    return sorted(results_list,key=lambda x:x["date"],reverse=True)

def get_tweets_data(condition):
    """
    つぶやきの内容をMongoDBから取得する
    :param condition: 検索の絞り込み条件（Dictionary）
    :return: JSON [{},...]
    """
    date_format = '%Y/%m/%d %H:%M:%S'
    results_list = []
    for tweet in tweet_collection.find(condition,{'created_datetime': 1, 'retweet_count': 1, 'id': 1, 'user': 1, 'text': 1, 'entities':1, 'retweeted_status': 1}):
        #retweetの場合は処理をしない。また、retweet以外は処理する。 
        if 'retweeted_status' in tweet:
            print('retweet!')
        else:    
            result = {'created_datetime': date_to_japan_time(tweet['created_datetime']).strftime(date_format),
              'retweet_count': tweet['retweet_count'], 'id': tweet['id'],
              'user.screen_name': tweet['user']['screen_name'], 'text': tweet['text']}
            
            #media_urlを持つtweetにはそのURLを保存する
            media_elements = tweet.get('entities').get('media')
            if media_elements != None:
                media_urls = []
                for media in media_elements:
                    media_url = media.get('media_url')
                    if media_url != None: media_urls.append(media_url)
                result['media_urls'] = ",".join(media_urls)
            
            results_list.append(result)

    for r in results_list :
        r['nouns'] =  split_text_only_noun(get_text_eliminated_some_pattern_words(r['text']))
        r['PrintID'] = ",".join(get_nps_printid(r['text']))

    #ツイートの作成日(created_datetime)で昇順ソートする
    return sorted(results_list,key=lambda x:x["created_datetime"])
    
### MeCab による単語への分割関数 (名詞のみ残す)
def split_text_only_noun(text):
    tagger = MeCab.Tagger()
    tagger.parse('')
    node = tagger.parseToNode(text)

    words = []
    while node:
        pos = node.feature.split(",")[0]
        if pos == "名詞":
            word = node.surface
            words.append(word)
        node = node.next
    return " ".join(words)
    
### TF-IDF の結果からi 番目のドキュメントの特徴的な上位 n 語を取り出す
def extract_feature_words(terms, tfidfs, i, n):
    tfidf_array = tfidfs[i]
    top_n_idx = tfidf_array.argsort()[-n:][::-1]
    words = [terms[idx] for idx in top_n_idx]
    return words
    
### twitter accountとURLを文字列から消す
def get_text_eliminated_some_pattern_words(text):    
    text_tmp = text
    
    twitter_account_pattern = r"@(.+?)\s"
    text_tmp = get_eliminated_text(twitter_account_pattern,text_tmp)
    
    url_pattern = r"http(.+?)($|\s)"
    text_tmp = get_eliminated_text(url_pattern,text_tmp)
    
    networkprint_id_pattern = r"[A-Z0-9]{10}"
    text_tmp = get_eliminated_text(networkprint_id_pattern,text_tmp)
    
    nps_id_pattern = r"[A-Z0-9]{8}"
    text_tmp = get_eliminated_text(nps_id_pattern,text_tmp) 
    
    hashtag_pattern =r"#(.+?)($|\s)"
    text_tmp = get_eliminated_text(hashtag_pattern,text_tmp)    
    
    return text_tmp

### 文字列にNPSの予約番号が含まれている場合、その予約番号を返す。含まれていない場合はから文字で返す。
def get_nps_printid(text):

    #Network Printの番号は10桁なので事前に削除する。
    networkprint_pattern = r"[A-Z0-9]{10}"
    text_tmp = get_eliminated_text(networkprint_pattern,text)
    
    nps_pattern = r"[A-Z0-9]{8}"
    iterator = re.finditer(nps_pattern,text_tmp,re.MULTILINE)
    
    print_ids = []
    
    for match in iterator:
        print_ids.append(match.group())
    
    return print_ids
    
### patternで指定した正規表現パターンの文字列を消す
def get_eliminated_text(pattern, text):
    iterator = re.finditer(pattern,text,re.MULTILINE)
    eliminated_text = text
    
    for match in iterator:
        eliminated_text = eliminated_text.replace(match.group(),'')
        
    return eliminated_text

#
def create_tweets_analyze_result(output_folder_path, start_date, end_date):
    
    for i in range(0, ANALYZE_DAYS) :
        date = start_date + datetime.timedelta(days=i)
        str_date = format(date.strftime('%Y%m%d'))
        file_path = output_folder_path + 'tweets_' + str_date + '.json'    

        if os.path.exists(file_path) == False:
            file = open(file_path,'w')
            condition = {'created_datetime': {'$gte': date, '$lt': date + datetime.timedelta(days=1)}}
            json.dump(get_tweets_data(condition),file)
            file.close()
            print(file_path)
 

    str_end_date = format(end_date.strftime('%Y%m%d'))
    str_start_date = format(start_date.strftime('%Y%m%d'))
    file_path = output_folder_path + 'feature_words_' + str_start_date + '-' + str_end_date + '.json'    
    
    file = open(file_path,'w')
    condition = {'created_datetime': {'$gte': start_date, '$lte': end_date}}
    json.dump(get_feature_words_from_tweets_text(condition,'%Y/%m/%d'),file)
    file.close()

## main
if __name__ == '__main__':
    
    d = datetime.datetime.now()
    date = datetime.datetime(d.year,d.month,d.day,0,0,0,0,timezone('Asia/Tokyo'))
    start_date = date - datetime.timedelta(days=ANALYZE_DAYS)
    print(start_date)
    
    date = datetime.datetime(d.year,d.month,d.day,23,59,59,999999,timezone('Asia/Tokyo'))
    end_date = date - datetime.timedelta(days=1)
    print(end_date)
        
    output_folder_path = config_feature_words.OUTPUT_FOLDER_PATH

    create_tweets_analyze_result(output_folder_path, start_date, end_date)