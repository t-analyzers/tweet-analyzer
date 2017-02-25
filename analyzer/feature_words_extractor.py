# -*- coding: utf-8 -*-
"""
archve.pyで取り込んだtweetsを分析する。
・分析内容：
　日にちごとの頻出単語トップXX
  XXはconfig_feature_words.pyで設定可能。
 
・出力ファイル：
　- 特徴語データ: feature_words_YYYYMMDD-YYYYMMDD.json
     [{"date": 日付, "tweet_count":ツイート数, "retweet_count":リツイート数,
       "posi_count":ポジティブツイート数, "nega_count":ネガティブツイート数,
       "feature_words":[特徴語リスト]},...] ※dateでソート
　- 日別ツイートデータ: tweets_YYYYMMDD.json
     [{'created_datetime': 日時,'retweet_count':収集時点のリツイート数, 
       'id': ツイートのID(文字列形式:id_str), user.screen_name': ツイッターアカウント名, 'text':ツイート本文, 'media_urls'(option):画像URL, 
       'PrintID'(option):プリント予約番号, 'retweet'(option):1 ※リツイートの場合に固定で入る項目}, ...] ※created_datetimeでソート
　- 特徴語データファイルリスト: filelist-feature_words.json: 
     特徴語データ出力先フォルダ内の特徴語データファイルのリスト（降順）。"feature_words_"で始まるファイルが対象。
　- ツイートファイルリスト: filelist-tweets.json
     日別ツイートデータ出力先フォルダ内の日別ツイートデータファイルのリスト（降順）。"tweets_"ではじまるファイルが対象。
　- 日別ワードクラウド画像: wordcloud_YYYYMMDD.png

       
@author: hitoshi
"""
from collections import defaultdict
import pymongo
import shared.datetime_extentions as dutil
import conf.config_feature_words as config
import datetime
from pytz import timezone
import json
import os.path
from os.path import join, relpath
from glob import glob
from wordcloud import WordCloud
import shared.text_utility as util

#形態素解析のライブラリ
import MeCab
#TF-IDFフィルタのクラス
from sklearn.feature_extraction.text import TfidfVectorizer

client = pymongo.MongoClient(config.HOST, config.PORT)
tweet_collection = client[config.DB_NAME][config.COLLECTION_NAME]

#分析するデータの日数
ANALYZE_DAYS =config.ANALYZE_DAYS
#抽出単語数
EXTRACT_FEATURE_WORDS_MAX = config.EXTRACT_FEATURE_WORDS_MAX
#TF-IDFパラメータ：　除外する合計出現回数
TFIDF_EXCLUDE_APPEARANCE = config.TFIDF_EXCLUDE_APPEARANCE

def create_tweets_analyze_result_file(output_folder_path, start_date, end_date):
    """
    ツイート分析（特徴語抽出）を実行し、結果をファイル(feature_words_YYYYMMDD-YYYYMMDD.json)に保存する。
    :param output_folder_path: 分析結果ファイルの保存先。
    :param start_datetime: 検索対象の開始時刻
    :param end_datetime: 検索対象の終了時刻
    """
    str_end_date = format(end_date.strftime('%Y%m%d'))
    str_start_date = format(start_date.strftime('%Y%m%d'))
    file_path = output_folder_path + 'feature_words_' + str_start_date + '-' + str_end_date + '.json'    

    #分析（特徴語抽出）を実行し、ファイルに保存する    
    file = open(file_path,'w')
    condition = {'created_datetime': {'$gte': start_date, '$lte': end_date}}
    json.dump(_get_feature_words_from_tweets_text(condition,'%Y/%m/%d'),file)
    file.close()
    
def _get_feature_words_from_tweets_text(condition, date_format, extract_feature_words_max=EXTRACT_FEATURE_WORDS_MAX):
    """
    日付フォーマットに合致するつぶやきの頻出名詞をJSON形式で返す
    :param condition: 検索の絞り込み条件（Dictionary）
    :param date_format: 日付フォーマット、指定されたフォーマットごとにつぶやき数を計算する
    :return: JSON [{},...]
    """
    
    tweets_count_dict = defaultdict(int) #集計時間単位（以下、わかりやすくするために「日別」とする）のtweet件数
    retweets_count_dict = defaultdict(int)
    nega_count_dict = defaultdict(int)
    posi_count_dict = defaultdict(int)
    nouns_dict = defaultdict(str) #「日別」のtweet textの名詞を連結した文字列
    words_dict = defaultdict(str)
    
    target_time_units =[] #date_formatで指定した年月日時文字列。例）date_format='%Y%m%d'の場合は'2016/06/01'のような日にちの配列になる。
    target_time_unit_nouns =[] #date_formatで指定した年月日時ごとのtweetに含まれる名詞を連結した文字列
    
    #tweetsの読み込み（mongoDBからのfind時のsortはメモリ不足でエラーになるため、ファイル出力前にこのプログラムでソートする）
    for tweet in tweet_collection.find(condition, {'_id': 1, 'created_datetime': 1,'retweeted_status': 1, 'text':1, 'negaposi':1}):
        str_date = dutil.date_to_japan_time(tweet['created_datetime']).strftime(date_format)
        
        #初めて処理する日付の場合はtarget_time_unitsに格納する
        if (str_date in target_time_units) == False :
            target_time_units.append(str_date)
            
        #その日の件数をカウントアップする
        tweets_count_dict[str_date] += 1 
        
        #そのツイートがretweetの場合はカウントアップする
        if 'retweeted_status' in tweet:
            retweets_count_dict[str_date] += 1
            
        #そのツイートがネガまはたポジ場合はカウントアップする
        if 'negaposi' in tweet:
            negaposi = tweet["negaposi"]
            if negaposi == 1 : 
                posi_count_dict[str_date] += 1
            elif negaposi == -1 :
                nega_count_dict[str_date] += 1
        
        #形態素解析で名詞を抽出して文字列として連結する
        nouns_dict[str_date] += " " + _split_text_only_noun(util.get_text_eliminated_some_pattern_words(tweet['text']))

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
        for x in  _extract_feature_words(terms, tfidfs, i, extract_feature_words_max):
            words_dict[target_time_units[i]].append(x)

    results_list =[]
    for i in range(0, len(target_time_units)) :
        result = {"date": target_time_units[i], 
                  "tweets_count": tweets_count_dict[target_time_units[i]], "retweets_count": retweets_count_dict[target_time_units[i]],
                  "posi_count": posi_count_dict[target_time_units[i]], "nega_count": nega_count_dict[target_time_units[i]],
                  "feature_words": words_dict[target_time_units[i]]}
        results_list.append(result)
    
    print(results_list)
    #dateで降順ソートする
    return sorted(results_list,key=lambda x:x["date"],reverse=True)
    
### MeCab による単語への分割関数 (名詞のみ残す)
def _split_text_only_noun(text):
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
def _extract_feature_words(terms, tfidfs, i, n):
    tfidf_array = tfidfs[i]
    top_n_idx = tfidf_array.argsort()[-n:][::-1]
    words = [terms[idx] for idx in top_n_idx]
    return words

def create_tweets_files(output_folder_path, start_date, end_date):
    """
    日別ツイートファイル(tweets_YYYYMMDD.json)を保存する。すでに存在していた場合は上書きせずスキップする。
    :param output_folder_path: 日別ツイートファイルの保存先。
    :param start_datetime: 検索対象の開始時刻
    :param end_datetime: 検索対象の終了時刻
    """
    for i in range(0, ANALYZE_DAYS) :
        date = start_date + datetime.timedelta(days=i)
        str_date = format(date.strftime('%Y%m%d'))
        file_path = output_folder_path + 'tweets_' + str_date + '.json'    
    
        if os.path.exists(file_path) == False:
            file = open(file_path,'w')
            condition = {'created_datetime': {'$gte': date, '$lt': date + datetime.timedelta(days=1)}}
            json.dump(_get_tweets_data(condition),file, indent=0)
            file.close()
            print(file_path)

def _get_tweets_data(condition):
    """
    つぶやきの内容をMongoDBから取得するして必要な項目を抽出する
    :param condition: 検索の絞り込み条件（Dictionary）
    :return: JSON [{},...]
    """

    #ツイートを取得しcreated_datetimeでソート
    tweets_tmp = []
    for tweet in tweet_collection.find(condition,{'created_datetime':1 ,'created_at': 1, 
                                                  'retweet_count': 1, 'id_str': 1, 'user': 1, 'text': 1, 'entities':1,
                                                  'retweeted_status': 1, 'negaposi':1, 'hash_match':1}):
        tweets_tmp.append(tweet)
    
    tweets = sorted(tweets_tmp,key=lambda x:x["created_datetime"])

    date_format = '%Y/%m/%d %H:%M:%S' 
    results_list = []
    for i in range(0,len(tweets)):
        tweet = tweets[i]
        #retweetの場合はフラグを立てる
        retweet_flag = False
        if 'retweeted_status' in tweet:
            retweet_flag = True

        #ツイート本文を比較する
        exist_flag = False
        for t in results_list :
            if(t['text']==tweet['text']):
                exist_flag = True
                break
        #すでにresult_listに含まれているツイートは処理しない
        if exist_flag == False:
            result = {'created_datetime': dutil.str_to_date_jp(tweet["created_at"]).strftime(date_format),
              'retweet_count': tweet['retweet_count'], 'id': tweet['id_str'],
              'user.screen_name': tweet['user']['screen_name'], 'text': tweet['text']}
            
            #media_urlを持つtweetにはそのURLを保存する
            media_elements = tweet.get('entities').get('media')
            if media_elements != None:
                media_urls = []
                for media in media_elements:
                    media_url = media.get('media_url')
                    if media_url != None: media_urls.append(media_url)
                result['media_urls'] = ",".join(media_urls)
                #result['media_urls'] = media_urls  ##media_urlsが複数入っているツイートは見たことないが、複数入る前提でリストにしておくのが良さそう。
            
            #プリント予約番号が抽出できたら保存する。
            printids = util.get_nps_printid(result['text'])
            if len(printids) > 0: result['PrintID'] = ",".join(printids)
                
            #リツイートの場合は印をつける
            if retweet_flag == True: result['retweet'] = 1
            
            #ネガポジの要素を含む場合はその値を保存する
            negaposi = tweet.get('negaposi')
            if negaposi != None: result['negaposi'] = negaposi
                
            #一致した画像のラベルを保存する
            hash_match = tweet.get('hash_match')
            if hash_match != None: result['hash_match'] = hash_match
            
            results_list.append(result)

    #ツイートの作成日(created_datetime)で昇順ソートする
    return sorted(results_list,key=lambda x:x["created_datetime"])


def create_word_cloud(output_folder_path, start_datetime, end_datetime):
    """
    MongoDBに格納されているつぶやきから日別の特徴語を抽出し、ワードクラウドを生成する。
    :param output_folder_path: ワードクラウド画像ファイルの保存先。
    :param start_datetime: 検索対象の開始時刻
    :param end_datetime: 検索対象の終了時刻
    """
    condition = {'created_datetime': {'$gte': start_datetime, '$lte': end_datetime}}
    feature_word_list = _get_feature_words_from_tweets_text(condition, '%Y/%m/%d', extract_feature_words_max=120)
    [_feature_word_to_word_cloud(output_folder_path, feature_word) for feature_word in feature_word_list]

def _feature_word_to_word_cloud(output_folder_path, feature_word):
    """
    特徴語からワードクラウドに変換する。
    outディレクトリ以下に日別の画像ファイルを出力する。
    :param output_folder_path: 出力先フォルダのパス
    :param feature_word: 特徴語
    """
    file_name = 'wordcloud_' + feature_word['date'].replace('/', '') + '.png'
    file_path = os.path.abspath(os.path.join(output_folder_path, file_name))
    # 特徴語の出現頻度は、リストの順番をもとに機械的に設定する。
    size = len(feature_word['feature_words'])
    array_of_tuples = [(word, size - idx) for idx, word in enumerate(feature_word['feature_words'])]
    _save_word_cloud_img(array_of_tuples, file_path)


def _save_word_cloud_img(frequencies, file_path):
    """
    ワードクラウドの画像ファイルを指定されたファイルパスに保存する。
    参考：http://amueller.github.io/word_cloud/index.html
    :param frequencies: タブル(単語, 出現頻度)のリスト
    :param file_path: 画像ファイルのパス
    """
    # 日本語フォントのパスが正しく設定されている必要がある。
    font_path = config.JAPANESE_FONT_PATH
    wc = WordCloud(background_color='white', max_font_size=320, font_path=font_path, width=900, height=500)
    wc.generate_from_frequencies(frequencies)
    wc.to_file(file_path)

def create_filelist(folder_path, target_filename_regexp, output_filename, count=7):
    """
    指定したフォルダパス内の正規表現にマッチするファイル名のリストファイルを作成する。
    :param folder_path: ファイル名を取得するフォルダのパス。また、リストファイルの保存先。
    :param target_filename_regexp: 取得するファイル名の正規表現。
    :param output_filename: リストファイルのファイル名
    """
    files_list = [relpath(x, folder_path) for x in glob(join(folder_path, target_filename_regexp))]
    files_list.sort(reverse=True)
    files_list_out = files_list[:count]
    output_file_path = folder_path + output_filename 

    output_file = open(output_file_path,'w')
    json.dump(files_list_out,output_file)
    output_file.close()

## main
if __name__ == '__main__':
    
    d = datetime.datetime.now()
    date = datetime.datetime(d.year,d.month,d.day,0,0,0,0,timezone('Asia/Tokyo'))
    start_date = date - datetime.timedelta(days=ANALYZE_DAYS)
    date = datetime.datetime(d.year,d.month,d.day,23,59,59,999999,timezone('Asia/Tokyo'))
    end_date = date - datetime.timedelta(days=1)
    print(start_date)
    print(end_date)

    #出力先パスを指定        
    output_folder_path = config.OUTPUT_FOLDER_PATH
    print("[info] 出力先パス： " + output_folder_path)
    
    #ツイート分析結果をファイルに保存する
    print("[info]ツイート分析開始")
    create_tweets_analyze_result_file(output_folder_path, start_date, end_date)
    #分析したツイートを日別ツイートファイルとして保存する（存在しないファイルを作成。上書きしない）
    print("[info] 日別ツイートファイル作成開始")
    create_tweets_files(output_folder_path, start_date, end_date)
    #分析したツイートの日別ワードクラウドを画像ファイルとして保存する（上書き）
    print("[info] 日別ワードクラウド作成開始")
    create_word_cloud(output_folder_path,start_date, end_date)
    
    #出力先フォルダ内の特徴語ファイルと日別ツイートファイルのリストを作成する（上書き）
    print("[info] ファイルリストの作成開始")
    create_filelist(output_folder_path, 'feature_words_*', 'filelist-feature_words.json')
    create_filelist(output_folder_path, 'tweets_*', 'filelist-tweets.json')
    
    print("[info] 処理完了")
