# -*- coding: utf-8 -*-
"""
metadata株式会社の「高精度ネガポジAPI」を使用してツイート本文のネガポジを判定する。
データ取得先、格納先はMongoDB。
・コンフィグファイル：config_metadata_api.py
 - ツイートの取得先：  INPUT_COLLECTION_NAME
 - 教師データ(metadata APIで取得した結果)の格納先： OUTPUT_COLLECTION_NAME
 　　格納内容
    {'created_datetime': 日時,'retweet_count':収集時点のリツイート数,  
       'id_str': ツイートのID(文字列形式:id_str), user_screen_name': ツイッターアカウント名, 
       'text':ツイート本文, 'media_urls:画像URL,
       'additional_info': {'metadata_api':{'negaposi_value': 「高精度ネガポジAPI」で取得したscore,
                                           'negaposi_int': 3値(1,0,-1)へ変換した値}}
     } 

Created on Wed Aug 10 22:41:35 2016
@author: hitoshi
"""

import config_metadata_api

import shared.datetime_extentions as dutil
import shared.text_utility as util
import urllib.request, urllib.parse
import datetime
from pytz import timezone
import json
import copy

import pymongo
client = pymongo.MongoClient(config_metadata_api.HOST, config_metadata_api.PORT)
input_collection = client[config_metadata_api.DB_NAME][config_metadata_api.INPUT_COLLECTION_NAME]
output_collection = client[config_metadata_api.DB_NAME][config_metadata_api.OUTPUT_COLLECTION_NAME]

def insert_learning_data_using_metadata(condition):
    """
    つぶやきの内容をMongoDBから取得する
    :param condition: 検索の絞り込み条件（Dictionary）
    :return: JSON [{},...]
    """
    date_format = '%Y/%m/%d %H:%M:%S'
    results_list = [] 
    counter = config_metadata_api.MAX_USAGE_COUNT
    
    for tweet in input_collection.find(condition,
                                       {'created_datetime': 1,'retweet_count': 1,'retweeted_status': 1,
                                        'id_str': 1, 'user': 1, 'text': 1, 'entities':1}):
        #retweet以外を取り出す。 
        if 'retweeted_status' not in tweet:            
            counter -= 1
            
            result = {'created_datetime': dutil.date_to_japan_time(tweet['created_datetime']).strftime(date_format),
              'retweet_count': tweet['retweet_count'], 'id': tweet['id_str'],
              'user_screen_name': tweet['user']['screen_name'], 'text': tweet['text']}
            
            negaposi_value = get_negaposi_metadata(util.get_text_eliminated_some_pattern_words(tweet['text']))
            negaposi_int = 0
            if negaposi_value > 0:
                negaposi_int = 1
            elif negaposi_value < 0:
                negaposi_int = -1
            result['additional_info'] = {"metadata_api":{"negaposi_value": negaposi_value,"negaposi_int": negaposi_int}}
            
            #media_urlを持つtweetにはそのURLを保存する
            media_elements = tweet.get('entities').get('media')
            if media_elements != None:
                media_urls = []
                for media in media_elements:
                    media_url = media.get('media_url')
                    if media_url != None: media_urls.append(media_url)
                result['media_urls'] = ",".join(media_urls)
            
            #resultをDBに単純にinsertすると、resultにも"_id"が自動で入ってしまいjson.dumpでエラーになる。
            #　→ insert用の変数を用意してcopyする。
            result_for_insert = copy.deepcopy(result)
            results_list.append(result)
            output_collection.insert_one(result_for_insert)
            
        if counter <= 0:
            break
    
    print(results_list)
    #ツイートの作成日(created_datetime)で昇順ソートする
    return sorted(results_list,key=lambda x:x["created_datetime"])
    
def get_negaposi_metadata(text):
    print("text: "+text)
    url = config_metadata_api.NEGAPOSI_URL_ENDPOINT + "?out=json"
    url += "&apikey=" + config_metadata_api.KEY
    url += "&text=" + urllib.parse.quote_plus(text,encoding="utf-8")
    print(url)

    with urllib.request.urlopen(url) as res:
        json_data = json.loads(res.read().decode("utf-8"))
        print(json_data)
        negaposi_value = json_data["negaposi"]    
        
        return negaposi_value

if __name__ == '__main__':
    
    DELTA_DATE = 1
    
    d = datetime.datetime.now()
    date = datetime.datetime(d.year,d.month,d.day,0,0,0,0,timezone('Asia/Tokyo'))
    start_date = date - datetime.timedelta(days=DELTA_DATE)
    print(start_date)
    
    date = datetime.datetime(d.year,d.month,d.day,23,59,59,999999,timezone('Asia/Tokyo'))
    end_date = date - datetime.timedelta(days=DELTA_DATE)
    print(end_date)

    condition = {'created_datetime': {'$gte': start_date, '$lt': end_date}}
    result = insert_learning_data_using_metadata(condition)

    print("■negaposi_value(metadata返値):")
    result = list(output_collection.aggregate([
        {"$group":{"_id":"$additional_info.metadata_api.negaposi_value","count":{"$sum":1}}},
        {"$sort": {"_id":1}}
        ]))
    for r in result:
        print(str(r["_id"]) + " : " + str(r["count"]) + "件")
    
    print("■negaposi_int(-1,0,1):")
    result = list(output_collection.aggregate([
        {"$group":{"_id":"$additional_info.metadata_api.negaposi_int","count":{"$sum":1}}},
        {"$sort": {"_id":1}}
        ]))
    for r in result:
        print(str(r["_id"]) + " : " + str(r["count"]) + "件")
