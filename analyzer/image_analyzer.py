# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 22:31:22 2017

画像を分析するための機能を実装。

@author: hitoshi
"""

import os,sys,re

import datetime
from pytz import timezone

import pymongo

import urllib.request
from urllib.error import URLError
import json

import base64

from sklearn import cross_validation
from PIL import Image
import numpy as np
import random, math

# Deep Learning (Keras)
from keras.models import Sequential
from keras.layers import Convolution2D, MaxPooling2D
from keras.layers import Activation, Dropout, Flatten, Dense

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
    
    def get_average_hash(self, img_file_path, size = config.RESIZE_PXL):
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
            
            ## 画像ファイルがなかったら取得。取得できなかったらスキップする
            if nutils.download_file_if_dont_exist(l["url"], file_path, file_name): continue
            
            img = Image.open(file_path)
            img = img.convert("RGB") # カラーモードの変更
            img = img.resize((config.IMG_SIZE, config.IMG_SIZE)) # 画像サイズの変更
            data = np.asarray(img)
                
            Y1 = [0 for i in range(len(config.ADULT_LABEL))]
            Y2 = [0 for i in range(len(config.CATEGORIES_LABEL))]
            
            ##
            annotation = l.get("annotation")
            if annotation == None : continue
            adult_label = annotation.get("adult")

            if adult_label == None : continue
            
            for i,ad in enumerate(config.ADULT_LABEL):  
                if adult_label == ad:
                    Y1[i] = 1
                    break

            label_annotations = annotation.get('labels')
            if label_annotations == None: continue
            
            for label in label_annotations:                   
                for i,cat in enumerate(config.CATEGORIES_LABEL):
                    if label == cat : 
                        Y2[i] = 1
                        break
                    
            X.append(data)
            Y.append(Y1+Y2)
                    
            if is_train == False: continue
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
        
        print("画像データ数:" + str(len(X)))
        X = np.array(X)
        Y = np.array(Y)
        
        return X,Y


    def make_learning_gcvdata(self, filelist, is_train):
        """
        GCVで作成した学習用データ(DB_LABELS_GCV_COLLECTION_NAME)を使用して学習する
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
            for i,ad in enumerate(config.GCV_ADULT_LABEL):  
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
                    
                for i,cat in enumerate(config.GCV_CATEGORIES_LABEL):
                    if label == cat and score > config.SCORE_UPPER : Y2[i] = score
            
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
        
        return X,Y

    # 全てのディレクトリを列挙
    def enum_all_files(self, path):
        for root, dirs, files in os.walk(path):
            for f in files:
                fname = os.path.join(root, f)
                if re.search(r'\.(jpg|jpeg|png)$', fname):
                    yield fname
        
    # モデルを構築 --- (※2)
    def build_model(self, in_shape):
        model = Sequential()
        
        model.add(Convolution2D(32, 3, 3, 
        	border_mode='same',
        	input_shape=in_shape))
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
        model.add(Activation('softmax'))
        model.compile(loss='binary_crossentropy',
        	optimizer='rmsprop',
        	metrics=['accuracy'])
        return model
    
    # モデルを訓練する --- (※3)
    def model_train(self, X, y):
        model = self.build_model(X.shape[1:])
        model.fit(X, y, batch_size=config.CNN_BATCH, nb_epoch=config.CNN_EPOCH)
        # モデルを保存する --- (※4)
        hdf5_file = config.CNN_FOLDER + config.CNN_MODEL_FILE
        model.save_weights(hdf5_file)
        return model
    
    # モデルを評価する --- (※5)
    def model_eval(self, model, X, y):
        score = model.evaluate(X, y)
        print('loss=', score[0])
        print('accuracy=', score[1])
    
    def predict_img_labels(self, filepath):
        # 入力画像をNumpyに変換 --- (※2)
        X = []
        files = []
        img = Image.open(filepath)
        img = img.convert("RGB")
        img = img.resize((config.IMG_SIZE, config.IMG_SIZE))
        in_data = np.asarray(img)
        X.append(in_data)
        files.append(filepath)
        X = np.array(X)
        
        # CNNのモデルを構築 --- (※3)
        model = self.build_model(X.shape[1:])
        model.load_weights(config.CNN_FOLDER + config.CNN_MODEL_FILE)
        
        # データを予測 --- (※4)
        pre = model.predict(X)
        label_all = config.ADULT_LABEL+config.CATEGORIES_LABEL
        for i,score in enumerate(pre[0]):
            print(label_all[i] + ": " + str(score))

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
        
        features = [{"type":"LABEL_DETECTION","maxResults":5},{"type":"SAFE_SEARCH_DETECTION","maxResults":1}]
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
        
        if len(results) > 1:  flag = True
            
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
        
if __name__ == "__main__" :
    arg_num = len(sys.argv)
    print(arg_num)
    print(sys.argv)

    #実行日時の前日(0:00-24:00)を指定する
    d = datetime.datetime.now()
    date = datetime.datetime(d.year,d.month,d.day,0,0,0,0,timezone('Asia/Tokyo'))
    start_datetime = date - datetime.timedelta(days=1)
    date = datetime.datetime(d.year,d.month,d.day,23,59,59,999999,timezone('Asia/Tokyo'))
    end_datetime = date - datetime.timedelta(days=0)
    
    # 引数が2以下の場合は終了する。
    if arg_num <= 2:
        exit
    
    #ハッシュによる類似画像チェック
    if sys.argv[1] == "hash": 
    
        avhash = AverageHash()  
        nwutil = NetworkUtilities()
        dao = DatabaseUtilities()
        
        img_url_list = dao.get_img_url_list(start_datetime,end_datetime)
        #print(img_url_list)
        
        for img_url in img_url_list:
            url = img_url["url"]
            folder_path = config.DOWNLOAD_IMG_FOLDER  + img_url["username"] + "/"
            filename = img_url["id_str"] + "_" + img_url["url"].split("/")[-1]
            
            result = nwutil.download_file_if_dont_exist(url, folder_path, filename)
            if result == True:
                avhash.update_match_hash(url, folder_path+filename, config.DIFF_RATIO, start_datetime,end_datetime)
                
    #Goovle Cloud Vision APIを使って教師データを作成
    elif sys.argv[1] == "gcv_labels":
        
        nwutil = NetworkUtilities()
        dao = DatabaseUtilities()
        
        img_url_list = dao.get_img_url_list(start_datetime,end_datetime)    
        
        for img_url in img_url_list:
            url = img_url["url"]
            folder_path = config.DOWNLOAD_IMG_FOLDER  + img_url["username"] + "/"
            filename = img_url["id_str"] + "_" + img_url["url"].split("/")[-1]
            
            # すでにDBにURLが存在している場合はスキップしてリストの次を処理する
            if dao.exist_check_img_url_in_db(config.DB_LABELS_GCV_COLLECTION_NAME,url) : continue           
            
            result = nwutil.download_file(url, folder_path, filename)
            if result == True:
                result_dic = nwutil.get_img_labels_using_GCV(folder_path+filename)
            else:
                continue
                
            if result_dic["success"] == True:
                dao.insert_one(config.DB_LABELS_COLLECTION_NAME, 
                               {"username": img_url["username"], "id_str": img_url["id_str"], 
                               "url": img_url["url"], "gcv_labels": result_dic["labels"]})
                               
    #画像ファイルをダウンロードする
    elif sys.argv[1] == "download":
        nwutil = NetworkUtilities()
        dao = DatabaseUtilities()
        img_url_list = dao.get_img_url_list(start_datetime,end_datetime)
        print("画像URL： " + str(len(img_url_list)))
        count = 0
        for img_url in img_url_list:
            url = img_url["url"]
            folder_path = config.DOWNLOAD_IMG_FOLDER  + img_url["username"] + "/"
            filename = img_url["id_str"] + "_" + img_url["url"].split("/")[-1]
            # すでにファイルが存在している場合はスキップしてリストの次を処理する
            if os.path.exists(folder_path + filename): continue

            result = nwutil.download_file(url, folder_path, filename)
            print(str(result))
            
            if result == True:  count = count+1
                
        print("ダウンロード件数：" + str(count))

    elif sys.argv[1] == "prepare":
        cnn = CNNImageAnalyzer()
        dao = DatabaseUtilities()
                
        all_labels = dao.find(config.DB_LABELS_COLLECTION_NAME,{})
        random.shuffle(all_labels)
        th = math.floor(len(all_labels) * 0.6)
        train = all_labels[0:th]
        test = all_labels[th:]
        X_train, y_train = cnn.make_learning_data(train, True)
        X_test, y_test = cnn.make_learning_data(test, False)
        xy = (X_train, X_test, y_train, y_test)
        os.remove(config.CNN_FOLDER+config.LEARNING_PACK_FILE)
        np.save(config.CNN_FOLDER+config.LEARNING_PACK_FILE, xy)
        print("ok,", len(y_train))
 
    elif sys.argv[1] == "prepare_gcv":
        cnn = CNNImageAnalyzer()
        
        allfiles =[]
        for f in cnn.enum_all_files(config.DOWNLOAD_IMG_FOLDER):
            allfiles.append(f)
        random.shuffle(allfiles)
        th = math.floor(len(allfiles) * 0.6)
        train = allfiles[0:th]
        test  = allfiles[th:]
        X_train, y_train = cnn.make_learning_gcvdata(train, True)
        X_test, y_test = cnn.make_learning_gcvdata(test, False)
        xy = (X_train, X_test, y_train, y_test)
        np.save(config.CNN_FOLDER+config.LEARNING_PACK_FILE, xy)
        print("ok,", len(y_train))
        
    elif sys.argv[1] == "train":
        X_train, X_test, y_train, y_test = np.load(config.CNN_FOLDER + config.LEARNING_PACK_FILE)
        # データを正規化する
        X_train = X_train.astype("float") / 256
        X_test  = X_test.astype("float")  / 256

        cnn = CNNImageAnalyzer()
        # モデルを訓練し評価する    
        model = cnn.model_train(X_train, y_train)
        cnn.model_eval(model, X_test, y_test)

    elif sys.argv[1] == "predict":
        img_filepath = sys.argv[2]
        cnn = CNNImageAnalyzer()
        cnn.predict_img_labels(img_filepath)
