# -*- coding: utf-8 -*-
"""
画像を分析するための機能を実装。
GCV APIで教師データを作成し、その教師データを使って学習する。

@author: hitoshi
"""

import os, sys, re

import datetime
from pytz import timezone

import pymongo

import urllib.request
from urllib.error import URLError
import json

import base64

from PIL import Image
import numpy as np
import random, math

# 設定ファイル
import conf.config_image_analyzer as config

class CNNImageAnalyzer():
    """
    CNNを使った画像分析用のクラス。
    """
    def __int__(self):
        super().__init__()

    def make_learning_gcvdata(self, filelist, is_train):
        """
        GCVで作成した学習用データ(DB_LABELS_GCV_COLLECTION_NAME)を使用して学習する
        （2017/4/6 放置しているので、使うためには修正が必要。） 
        """
        # フォルダごとの画像データを読み込む --- (※2)
        X = [] # 画像データ
        Y = [] # ラベルデータ

        dao = DatabaseUtilities()

        for f in filelist:
            img = Image.open(f)
            img = img.convert("RGB") # カラーモードの変更
            img = img.resize((config.IMG_SIZE, config.IMG_SIZE)) # 画像サイズの変更
    #        img.thumbnail((image_size, image_size)) # 縦横比を保ったまま画像サイズの変更
            data = np.asarray(img)

            fname = f.split("/")[-1]
            str_id = fname.split("_")[0]
            uname = f.split("/")[-2]

            results = []
            for result in dao.find(config.DB_LABELS_GCV_COLLECTION_NAME, {"id_str": str_id, "username": uname}):
                results.append(result)

            #DBに存在しない場合はforループの先頭に戻る
            if len(results) == 0: continue

            Y1 = [0 for i in range(len(config.GCV_ADULT_LABEL))]
            Y2 = [0.0 for i in range(len(config.GCV_CATEGORIES_LABEL))]
            ##
            safe_annotations = results[0]['gcv_labels'][0]
            safe_annotations = safe_annotations.get('safeSearchAnnotation')
            if safe_annotations == None: continue

            adult_label = safe_annotations["adult"]
            for i, ad in enumerate(config.GCV_ADULT_LABEL):
                if adult_label == ad:
                    Y1[i] = 1
                    break
            ##
            label_annotations = results[0]['gcv_labels'][0]
            label_annotations = label_annotations.get('labelAnnotations')
            if label_annotations == None: continue

            for label_annotation in label_annotations:
                label = label_annotation['description']
                score = label_annotation['score']

                for i, cat in enumerate(config.GCV_CATEGORIES_LABEL):
                    if label == cat and score > config.SCORE_UPPER: Y2[i] = score

            if sum(Y2) > 0: #label annotationのscoreを持つ画像のみ学習データとして採用する。
                X.append(data)
                Y.append(Y1+Y2)

                if is_train == True: continue
                #5度ずつの回転＋反転で学習データを増やす
                for ang in range(-20, 20, 5):
                    img2 = img.rotate(ang)
                    data = np.asarray(img2)
                    X.append(data)
                    Y.append(Y1+Y2)
                    # 反転する
                    img2 = img2.transpose(Image.FLIP_LEFT_RIGHT)
                    data = np.asarray(img2)
                    X.append(data)
                    Y.append(Y1+Y2)
        X = np.array(X)
        Y = np.array(Y)

        return X, Y

    # 全てのディレクトリを列挙
    def enum_all_files(self, path):
        for root, dirs, files in os.walk(path):
            for f in files:
                fname = os.path.join(root, f)
                if re.search(r'\.(jpg|jpeg|png)$', fname):
                    yield fname

class NetworkUtilities():
    """
    通信用のユーティリティクラス。
    """
    def __int__(self):
        """
        初期化
        """
        super().__init__()


    def download_file(self, url, folder_path, filename):
        """
        指定したURLからファイルをダウンロードする機能。
        :param str url: ダウンロードするファイルのURL
        :param str folder_path: ダウンロードしたファイルの保存先フォルダ
        :param str filename: 保存するファイル名
        :return: 正常にファイル保存が完了した時はTrue、失敗時はFalse
        """
        #画像ダウンロード用のフォルダがない場合は作成する
        if not os.path.exists(config.DOWNLOAD_IMG_FOLDER):
            os.mkdir(config.DOWNLOAD_IMG_FOLDER)
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)

        try:
            #画像をダウンロード
            urllib.request.urlretrieve(url, folder_path+filename)
        except URLError as e:
            if hasattr(e, 'reason'):
                print('We failed to reach a server.')
                print('Reason: ', e.reason)
            elif hasattr(e, 'code'):
                print('The server couldn\'t fulfill the request.')
                print('Error code: ', e.code)

            return False #exceptionが発生した場合

        print("download " + url + " to " + folder_path+filename)
        return True #正常終了した場合

    def download_file_if_dont_exist(self, url, folder_path, filename):
        """
        指定したURLからダウンロードしていない場合、ファイルをダウンロードする機能。
        :param str url: ダウンロードするファイルのURL
        :param str folder_path: ダウンロードしたファイルの保存先フォルダ
        :param str filename: 保存するファイル名
        :return: 正常にファイル保存が完了した時はTrue、失敗時はFalse
        """

        result = True
        #画像ファイルがダウンロードされていない時はダウンロードを実行する
        if not os.path.exists(folder_path+filename):
            result = self.download_file(url, folder_path, filename)

        return result

    def get_img_labels_using_GCV(self, file_path):

        url = "https://vision.googleapis.com/v1/images:annotate?key="+config.GCP_KEY
        features = [{"type":"LABEL_DETECTION", "maxResults":5}, {"type":"SAFE_SEARCH_DETECTION", "maxResults":1}]
        #画像ファイルをbase64でencodeして読み込む
        file = open(file_path, 'rb').read()
        img64 = base64.b64encode(file).decode('utf-8')

        # POSTパラメータを設定する
        req_params = {"requests":
                [{"image": {"content": img64}, "features": features}]
            }
        # POSTパラメータをJSON形式に変形。また、文字コードをUTF-8にする
        req_params_json = json.dumps(req_params).encode("utf-8")

        try:
            request = urllib.request.Request(url, data=req_params_json, 
                                             method="POST", headers={"Content-Type" : "application/json"})
            with urllib.request.urlopen(request) as response:
                response_body = response.read().decode("utf-8")
                result = json.loads(response_body)["responses"]

            return {"success": True, "labels": result}

        except URLError as e:
            if hasattr(e, 'reason'):
                print('We failed to reach a server.')
                print('Reason: ', e.reason)
            elif hasattr(e, 'code'):
                print('The server couldn\'t fulfill the request.')
                print('Error code: ', e.code)

            return {"success": False}

class DatabaseUtilities():
    """
    DBアクセス用のユーティリティクラス。
    """

    #connection mongoDB
    client = pymongo.MongoClient(config.DB_HOST, config.DB_PORT)

    def __int__(self):
        """
        初期化
        """
        super().__init__()

    def get_img_url_list(self, start_datetime: datetime, end_datetime: datetime):
        """
        画像のURLをもつtweetをDBから抽出する。
        :param start_datetime,end_datetime: 検索する日付の範囲
        :return: 画像のURLをもつtweetのリスト
        """
        search_condition = {'created_datetime': {'$gte': start_datetime, '$lte': end_datetime}}

        tweets = self.client[config.DB_NAME][config.DB_TWEETS_COLLECTION_NAME]
        results = []
        for tweet in tweets.find(search_condition, {'id_str': 1, 'user': 1, 'entities':1}):
            #media_urlを持つtweetにはそのURLを保存する
            media_elements = tweet.get('entities').get('media')
            if media_elements != None:
                for media in media_elements:
                    media_url = media.get('media_url')
                    if media_url != None:
                        result = {}
                        result["url"] = media_url
                        result["username"] = tweet['user']['screen_name']
                        result["id_str"] = tweet['id_str']
                        results.append(result)
        return results

    def exist_check_img_url_in_db(self, collection_name, url):
        """
        指定したURLがDBの教師データ内に存在しているかどうかチェックする
        :param str url: チェックするURL
        :retrun: True or False
        """
        labels = self.client[config.DB_NAME][collection_name]
        results = []
        for result in labels.find({"url": url}):
               results.append(result)
        flag = False

        if len(results) > 1:flag = True
            
        return flag

    def update_many(self, collection, condition, key_value):
        """
        conditonで指定したドキュメントをアップデートする。
        :param conditon: アップデート対象の条件
        :param key_value: セットする値 {"key": value}
        """
        tweets = self.client[config.DB_NAME][config.DB_TWEETS_COLLECTION_NAME]
        tweets.update_many(condition, {'$set': key_value})

    def insert_one(self, collection, insert_set):
        """
        DBに1レコード追加する。
        :param collection:　追加対象のcollection
        :param insert_set: 追加レコード

        """
        labels = self.client[config.DB_NAME][collection]
        labels.insert_one(insert_set)

    def find(self, collection, condition):
        """
        DBを検索する
        :param collection:　検索対象のcollection
        :param condition: 検索条件
        """
        #labels = self.client[config.DB_NAME][collection]
        #return labels.find(condition)
        labels = []
        for l in self.client[config.DB_NAME][collection].find(condition):
            labels.append(l)

        return labels

if __name__ == "__main__":
    arg_num = len(sys.argv)
    print(sys.argv)

    #実行日時の前日(0:00-24:00)を指定する
    d = datetime.datetime.now()
    date = datetime.datetime(d.year, d.month, d.day, 0, 0, 0, 0, timezone('Asia/Tokyo'))
    start_datetime = date - datetime.timedelta(days=1)
    date = datetime.datetime(d.year, d.month, d.day, 23, 59, 59, 999999, timezone('Asia/Tokyo'))
    end_datetime = date - datetime.timedelta(days=0)

    # 引数が2以下の場合は終了する。
    if arg_num <= 2:
        exit
    #Goovle Cloud Vision APIを使って教師データを作成
    elif sys.argv[1] == "get_gcv_labels":
        nwutil = NetworkUtilities()
        dao = DatabaseUtilities()

        img_url_list = dao.get_img_url_list(start_datetime, end_datetime)

        for img_url in img_url_list:
            url = img_url["url"]
            folder_path = config.DOWNLOAD_IMG_FOLDER  + img_url["username"] + "/"
            filename = img_url["id_str"] + "_" + img_url["url"].split("/")[-1]

            # すでにDBにURLが存在している場合はスキップしてリストの次を処理する
            if dao.exist_check_img_url_in_db(config.DB_LABELS_GCV_COLLECTION_NAME, url) : continue

            result = nwutil.download_file(url, folder_path, filename)
            if result == True:
                result_dic = nwutil.get_img_labels_using_GCV(folder_path+filename)
            else:
                continue

            if result_dic["success"] == True:
                dao.insert_one(config.DB_LABELS_COLLECTION_NAME, 
                               {"username": img_url["username"], "id_str": img_url["id_str"], 
                               "url": img_url["url"], "gcv_labels": result_dic["labels"]})

    elif sys.argv[1] == "prepare":
        cnn = CNNImageAnalyzer()
        allfiles = []
        for f in cnn.enum_all_files(config.DOWNLOAD_IMG_FOLDER):
            allfiles.append(f)
        random.shuffle(allfiles)
        th = math.floor(len(allfiles) * 0.6)
        train = allfiles[0:th]
        test = allfiles[th:]
        X_train, y_train = cnn.make_learning_gcvdata(train, True)
        X_test, y_test = cnn.make_learning_gcvdata(test, False)
        xy = (X_train, X_test, y_train, y_test)
        np.save(config.CNN_FOLDER+config.LEARNING_PACK_FILE, xy)
        print("ok,", len(y_train))
