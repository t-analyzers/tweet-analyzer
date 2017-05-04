# -*- coding: utf-8 -*-
"""
画像を分析するための以下の機能を実装。
・ハッシュによる類似画像判定
・機械学習による画像分類
機械学習のライブラリにはKerasを使用。

@author: hitoshi
"""

import os, sys, re

import datetime
from pytz import timezone

import pymongo

import urllib.request
from urllib.error import URLError

from PIL import Image
import numpy as np
import random
import math

# Deep Learning (Keras)
from keras.models import Sequential
from keras.layers import Convolution2D, MaxPooling2D
from keras.layers import Activation, Dropout, Flatten, Dense
from keras import backend

# 設定ファイル
import conf.config_image_analyzer as config

class AverageHash():
    """
    AverageHashで類似画像を検出するためのクラス。
    """

    def __int__(self):
        """
        初期化
        """
        super().__init__()

    def get_average_hash_and_make_cache(self, img_file_path, size = config.RESIZE_PXL):
        """
        画像データのAverage Hashを取得する。すでに作成されている場合はキャッシュフォルダから取得する。存在しない場合は作成し、キャッシュフォルダに保存する。
        :param str img_file_path: 対象の画像ファイルパス
        :param int size: Average Hashを作成のために画像をリサイズする時のピクセル数。
        :return: np.ndarray（NumPyの配列）
        """
        #ハッシュをキャッシュするフォルダがない場合は作成する
        if not os.path.exists(config.CHECK_IMG_HASH_FOLDER):
            os.mkdir(config.CHECK_IMG_HASH_FOLDER)

        img_file_path_tmp = img_file_path[len(config.CHECK_IMG_FOLDER):]
        hash_file_path = config.CHECK_IMG_HASH_FOLDER + img_file_path_tmp.replace('/', '_') + ".csv"

        if not os.path.exists(hash_file_path):  # Hash値を算出し、CSVファイルに保存（キャッシュ）する
            hash_array = self.get_average_hash(img_file_path)
            np.savetxt(hash_file_path, hash_array, fmt="%.0f", delimiter=",")
        else: # 既にキャッシュがあればファイルから読み込み
            hash_array = np.loadtxt(hash_file_path, delimiter=",")
        return hash_array

    def get_average_hash(self, img_file_path, size=config.RESIZE_PXL):
        """
        画像データのAverage Hashを算出する。
        :param str img_file_path: 対象の画像ファイルパス
        :param int size: Average Hashを作成のために画像をリサイズする時のピクセル数。
        :return: np.ndarray（NumPyの配列）
        """
        img = Image.open(img_file_path)
        img = img.convert('L').resize((size, size), Image.ANTIALIAS)
        pixels = np.array(img.getdata()).reshape((size, size))
        avg = pixels.mean()
        hash_array = 1 * (pixels > avg)
        return hash_array

    def _hamming_dist(self, hash1, hash2):
        """
        ハミング距離（ハッシュ値の違い）を求める.
        :param np.ndarray hash1,hash2:  比較するハッシュ値（NumPyの配列）
        :return: ハミング距離（整数）
        """
        a = hash1.reshape(1, -1) # 1次元の配列に変換
        b = hash2.reshape(1, -1)
        dist = (a != b).sum()
        return dist

    def _enum_all_files(self, path):
        """
        指定したフォルダ配下に存在する画像ファイル(JPEG,PNG)のパスを列挙
        :param str path: フォルダのパス
        :return: 画像ファイルパスのリスト（厳密にはリストではない様子）
        """
        for root, dirs, files in os.walk(path):
            for f in files:
                fname = os.path.join(root, f)
                if re.search(r'\.(jpg|jpeg|png)$', fname):
                    yield fname

    def update_match_hash(self, img_url, img_file, rate, start_datetime, end_datetime):
        """
        あらかじめ特定のフォルダ(config.CHECK_IMG_FOLDER)に格納された画像と、
        img_fileで指定したローカルの画像ファイルをAverageHashで比較し、差分(0.0-1.0)がrate以下の場合に一致しているとみなす。
        一致している画像のURLをもつtweetに{"hash_match": "一致した画像のファイル名（拡張子除く）"}を設定する。
        :param str img_file:　チェック用の画像と比較する画像ファイルのパス
        :param str img_url: 上記ファイルのURL
        :param float rate:  一致しているとみなすハッシュ値の差分比率の閾値(0.0-1.0)
        """
        dao = DatabaseUtilities()
        src = self.get_average_hash(img_file)
        for check_file in self._enum_all_files(config.CHECK_IMG_FOLDER):
            dst = self.get_average_hash_and_make_cache(check_file)
            diff_r = self._hamming_dist(src, dst) / 256

            if diff_r < rate:
                print("MATCH!  (diff: " + str(diff_r) + ")")
                print(" - SRC: " + img_file)
                print(" - DST: " + check_file)
                matched_file_name = check_file.split("/")[-1]
                matched_file_name = matched_file_name.split(".")[-2]

                search_condition = {'created_datetime': {'$gte': start_datetime, '$lte': end_datetime}, 
                                    'entities.media.media_url': img_url}
                dao.update_many(config.DB_TWEETS_COLLECTION_NAME, search_condition, {'hash_match': matched_file_name})

class CNNImageAnalyzer():
    """
    CNNを使った画像分析用のクラス。
    """
    def __int__(self):
        super().__init__()

    def make_learning_data(self, labels, is_train):
        """
        学習用データ(DB_LABELS_COLLECTION_NAME)を使用して学習する
        """
        # フォルダごとの画像データを読み込む --- (※2)
        X = [] # 画像データ
        Y = [] # ラベルデータ
        print("・トレーニング？：" + str(is_train))
        print("・教師データ（ラベル数）：" + str(len(labels)))
        for l in labels:
            folder_path = config.DOWNLOAD_IMG_FOLDER + l["screen_name"] + "/"
            file_name = l["id"] + "_" + l["url"].split("/")[-1]
            file_path = folder_path + file_name

            nutils = NetworkUtilities()

            ## 画像ファイルがなかったら取得。取得できなかったら以降の処理をスキップする
            result = nutils.download_file_if_dont_exist(l["url"], folder_path, file_name)
            if result == False:
                print("skip")
                continue

            img = Image.open(file_path)
            img = img.convert("RGB") # カラーモードの変更
            img = img.resize((config.IMG_SIZE, config.IMG_SIZE)) # 画像サイズの変更
            data = np.asarray(img)

            label_list = [0 for i in range(len(config.CATEGORIES_LABEL))]

            ## annotation要素を含まなかった場合は以降の処理をスキップ
            annotation = l.get("annotation")
            if annotation == None: continue

            ## labels要素を含まなかった場合は以降の処理をスキップ
            label_annotations = annotation.get('labels')
            if label_annotations == None: continue

            for label in label_annotations:
                for i, cat in enumerate(config.CATEGORIES_LABEL):
                    if label == cat:
                        label_list[i] = 1
                        break

            X.append(data)
            Y.append(label_list)

            if is_train == False: continue

            #5度ずつの回転＋反転で学習データを増やす
            for ang in range(-20, 20, 5):
                img_tmp = img.rotate(ang)
                data = np.asarray(img_tmp)
                X.append(data)
                Y.append(label_list)

                # 反転する
                img_tmp = img_tmp.transpose(Image.FLIP_LEFT_RIGHT)
                data = np.asarray(img_tmp)
                X.append(data)
                Y.append(label_list)

        print("画像データ数:" + str(len(X)))
        X = np.array(X)
        Y = np.array(Y)

        return X, Y

    
    def enum_all_files(self, path):
        '''
        全てのディレクトリを列挙
        '''
        for root, dirs, files in os.walk(path):
            for f in files:
                fname = os.path.join(root, f)
                if re.search(r'\.(jpg|jpeg|png)$', fname):
                    yield fname

    def build_model(self, in_shape):
        '''
        学習モデルを構築
        '''
        model = Sequential()

        model.add(Convolution2D(32, 3, 3, border_mode='same', input_shape=in_shape))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Dropout(0.25))

        model.add(Convolution2D(64, 3, 3, border_mode='same'))
        model.add(Activation('relu'))
        model.add(Convolution2D(64, 3, 3))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Dropout(0.25))

        model.add(Flatten())
        model.add(Dense(1024))
        model.add(Activation('relu'))
        model.add(Dropout(0.5))

        model.add(Dense(config.LABEL_NUM))
        # multi-labelの分類にはsigmoidが良いらしい
        # https://github.com/odanado/Indeed-ML/issues/2
        model.add(Activation('sigmoid'))
        model.compile(loss='binary_crossentropy', optimizer='rmsprop', metrics=['accuracy'])
        return model

    def model_train(self, X, y):
        '''
        学習モデルを訓練し、ファイルとして保存する。
        :param numpy.array X: 訓練用の画像データのリスト
        :param numpy.array y: 訓練用の画像に対する分類ラベルのリスト
        '''
        model = None
        hdf5_file = config.CNN_FOLDER + config.CNN_MODEL_FILE
        model = self.build_model(X.shape[1:])
        model.fit(X, y, batch_size=config.CNN_BATCH, nb_epoch=config.CNN_EPOCH)

        # モデルを保存する
        model.save_weights(hdf5_file)

        backend.clear_session()

        return model

    def model_eval(self, model, X, y):
        '''
        学習モデルを評価する
        :param numpy.array X: 評価用の画像データのリスト
        :param numpy.array y: 評価用の画像に対する分類ラベルのリスト
        '''
        score = model.evaluate(X, y)
        print('loss=', score[0])
        print('accuracy=', score[1])
        backend.clear_session()

    def predict_img_labels(self, filepath, model_file_name = config.CNN_MODEL_FILE):
        '''
        学習モデルを使い、指定されたファイルの画像の分類を行う。
        :param str filepath: 分類対象の画像ファイルのパス
        :param str model_file_name: 学習モデルのファイル名
        '''
        file_name = model_file_name
        hdf5_file = config.CNN_FOLDER + file_name
        label_all = config.CATEGORIES_LABEL

        # 入力画像をNumpyに変換
        X = []
        img = Image.open(filepath)
        img = img.convert("RGB")
        img = img.resize((config.IMG_SIZE, config.IMG_SIZE))
        in_data = np.asarray(img)
        X.append(in_data)
        X = np.array(X)

        # CNNのモデルを構築
        model = self.build_model(X.shape[1:])
        model.load_weights(hdf5_file)

        # データを予測
        pre = model.predict(X)

        values ={}
        print(filepath)
        for i, score in enumerate(pre[0]):
            if score > 0.0:
                print(label_all[i] + ": " + str(score))
                values[label_all[i]] = score

        backend.clear_session()
        
        return values

    def update_labels(self, img_url, labels, start_datetime, end_datetime):
        """
        :param str img_url: ファイルのURL
        :param str labels:　画像に割り当てるラベル
        """
        dao = DatabaseUtilities()
        search_condition = {'created_datetime': {'$gte': start_datetime, '$lte': end_datetime}, 
                            'entities.media.media_url': img_url}
        dao.update_many(config.DB_TWEETS_COLLECTION_NAME, search_condition, {'labels': labels})

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
        except Exception as e:
            print("Exception happend at " + url) 
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
        media_urls = []
        for tweet in tweets.find(search_condition, {'id_str': 1, 'user': 1, 'entities':1}):
            #media_urlを持つtweetにはそのURLを保存する
            media_elements = tweet.get('entities').get('media')
            if media_elements != None:
                for media in media_elements:
                    media_url = media.get('media_url')
                    if (media_url != None) and not (media_url in media_urls):
                        media_urls.append(media_url)
                        result = {"url": media_url, "username": tweet['user']['screen_name'], "id_str": tweet['id_str']}
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

        if len(results) > 1:
            flag = True

        return flag

    def update_many(self, collection, condition, key_value):
        """
        conditonで指定したドキュメントをアップデートする。
        :param conditon: アップデート対象の条件
        :param key_value: セットする値 {"key": value}
        """
        tweets = self.client[config.DB_NAME][collection]
        result = tweets.update_many(condition, {'$set': key_value})
        return result

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
        print("パラメータが必要です")
        print(" * prepare : 機械学習のための教師データ（画像ファイルと画像に対しての分類ラベル）を1つのファイル(拡張子：npy)にまとめて生成")
        print(" * train : prepareで生成した教師データを使って学習モデルファイル(拡張子：hdf5)を生成")
        print(" * predict <filepath>: trainで生成した学習モデルを使用して<filepath>の画像を分類した結果を表示")
        print(" * predict2db : 学習モデルを使用し、実行日前日1日分のツイートに含まれる画像ファイルの分類を行いDB内のツイートに分類結果を付加")
        print(" * hash : ハッシュによる類似画像チェックを行いDB内のツイートに結果を付加")
        print(" * download : ツイートに含まれる画像をダウンロード")
        exit

    #ハッシュによる類似画像チェック
    elif sys.argv[1] == "hash":
        begin_datetime = datetime.datetime.now()
        avhash = AverageHash()
        nwutil = NetworkUtilities()
        dao = DatabaseUtilities()

        img_url_list = dao.get_img_url_list(start_datetime, end_datetime)

        for img_url in img_url_list:
            url = img_url["url"]
            folder_path = config.DOWNLOAD_IMG_FOLDER  + img_url["username"] + "/"
            filename = img_url["id_str"] + "_" + img_url["url"].split("/")[-1]

            result = nwutil.download_file_if_dont_exist(url, folder_path, filename)
            if result == True:
                avhash.update_match_hash(url, folder_path+filename, config.DIFF_RATIO, start_datetime, end_datetime)

        finish_datetime = datetime.datetime.now()
        print("begin: " + str(begin_datetime))
        print("finish: " + str(finish_datetime))
        print("time: " + str(finish_datetime - begin_datetime))

    #画像ファイルをダウンロードする
    elif sys.argv[1] == "download":
        nwutil = NetworkUtilities()
        dao = DatabaseUtilities()
        img_url_list = dao.get_img_url_list(start_datetime, end_datetime)
        print("画像URL： " + str(len(img_url_list)))
        count = 0
        for img_url in img_url_list:
            url = img_url["url"]
            folder_path = config.DOWNLOAD_IMG_FOLDER  + img_url["username"] + "/"
            filename = img_url["id_str"] + "_" + img_url["url"].split("/")[-1]
            # すでにファイルが存在している場合はスキップしてリストの次を処理する
            if os.path.exists(folder_path + filename):
                print(folder_path + filename)
                continue

            result = nwutil.download_file(url, folder_path, filename)

            if result == True:
                count = count + 1

        print("ダウンロード件数：" + str(count))

    elif sys.argv[1] == "prepare":
        begin_datetime = datetime.datetime.now()
        print("begin: " + str(begin_datetime))
        cnn = CNNImageAnalyzer()
        dao = DatabaseUtilities()
        all_labels = dao.find(config.DB_LABELS_COLLECTION_NAME, {})
        random.shuffle(all_labels)
        th = math.floor(len(all_labels) * 0.6)
        train = all_labels[0:th]
        test = all_labels[th:]
        X_train, y_train = cnn.make_learning_data(train, True)
        X_test, y_test = cnn.make_learning_data(test, False)
        xy = (X_train, X_test, y_train, y_test)
        if os.path.exists(config.CNN_FOLDER+config.LEARNING_PACK_FILE):
            os.remove(config.CNN_FOLDER+config.LEARNING_PACK_FILE)
        print("  save start: " + str(datetime.datetime.now()))
        np.save(config.CNN_FOLDER+config.LEARNING_PACK_FILE, xy)
        finish_datetime = datetime.datetime.now()
        print("finish: " + str(finish_datetime))
        print("time: " + str(finish_datetime - begin_datetime))
        print("ok,", len(y_train))

    elif sys.argv[1] == "train":
        begin_datetime = datetime.datetime.now()

        X_train, X_test, y_train, y_test = np.load(config.CNN_FOLDER + config.LEARNING_PACK_FILE)
        # データを正規化する
        X_train = X_train.astype("float") / 256
        X_test = X_test.astype("float")  / 256

        cnn = CNNImageAnalyzer()
        # モデルを訓練し評価する
        model = cnn.model_train(X_train, y_train)
        cnn.model_eval(model, X_test, y_test)

        finish_datetime = datetime.datetime.now()
        print("begin: " + str(begin_datetime))
        print("finish: " + str(finish_datetime))
        print("time: " + str(finish_datetime - begin_datetime))

    elif sys.argv[1] == "predict":
        img_filepath = ""
        label = None
        if arg_num == 3:
            img_filepath = sys.argv[2]
        elif arg_num == 4:
            label = sys.argv[2]
            img_filepath = sys.argv[3]

        cnn = CNNImageAnalyzer()
        cnn.predict_img_labels(img_filepath)

    elif sys.argv[1] == "predict2db":
        begin_datetime = datetime.datetime.now()

        nwutil = NetworkUtilities()
        dao = DatabaseUtilities()
        img_url_list = dao.get_img_url_list(start_datetime, end_datetime)
        model_files = config.CNN_MODEL_FILES
        
        img_urls = []
        img_filepaths = []
        for img_url in img_url_list:
            url = img_url["url"]
            folder_path = config.DOWNLOAD_IMG_FOLDER  + img_url["username"] + "/"
            filename = img_url["id_str"] + "_" + img_url["url"].split("/")[-1]
            result = nwutil.download_file_if_dont_exist(url, folder_path, filename)
            print(folder_path + filename)
            if result == True:
                img_urls.append(url)
                img_filepaths.append(folder_path + filename)
        
        cnn = CNNImageAnalyzer()

        for i, img_url in enumerate(img_urls):
            labels = []
            for mfile in model_files:
                label_values = cnn.predict_img_labels(img_filepaths[i], model_file_name=mfile)
                for label in label_values:
                    if (label_values[label] > 0.9) and (label not in labels):
                        labels.append(label)

            search_condition = {}
            search_condition['created_datetime'] = {'$gte': start_datetime, '$lte': end_datetime}
            search_condition['entities.media.media_url'] = img_url
            result = dao.update_many(config.DB_TWEETS_COLLECTION_NAME, search_condition, {'labels': labels})
            print("*url: " + img_url + " *label: " + str(labels) + " *update count:" + str(result.matched_count))

        finish_datetime = datetime.datetime.now()
        print("begin: " + str(begin_datetime))
        print("finish: " + str(finish_datetime))
        print("time: " + str(finish_datetime - begin_datetime))
        print("target images: " + str(len(img_url_list)))