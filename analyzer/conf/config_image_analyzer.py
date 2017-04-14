# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 22:37:43 2017

image_analyzer.py用の設定ファイル

@author: hitoshi
"""

## mongodbの設定
DB_HOST = "localhost"
DB_PORT = 27017
DB_NAME = "twitter-archive"
DB_TWEETS_COLLECTION_NAME = "tweets"
DB_LABELS_GCV_COLLECTION_NAME = "img_labels_gcv"
DB_LABELS_COLLECTION_NAME = "img_labels"

## ファイルパスの指定
# データ用のルートフォルダ
DATA_FOLDER = "../data/"
#ダウンロードする画像を格納するフォルダ
DOWNLOAD_IMG_FOLDER = DATA_FOLDER + "download/"

## Average Hash
# Average Hashで比較するための画像とそのハッシュ値を格納するフォルダ
CHECK_IMG_FOLDER = DATA_FOLDER + "check_img/"
CHECK_IMG_HASH_FOLDER = DATA_FOLDER + "check_img_hash/"
# Average Hashを作成するときの縮小画像サイズ（縦横のピクセル数）
RESIZE_PXL = 16
# 類似と判定する画像のハッシュ値差異の割合(0-1.0)
DIFF_RATIO = 0.1

## Google Cloud Vision APIを使うときのAPIキー
GCP_KEY = ""

## CNN
CNN_FOLDER = DATA_FOLDER + "cnn/"
# 教師データの画像ピクセル数
IMG_SIZE = 128
#学習用に画像とラベルの一式をまとめた教師データファイル
LEARNING_PACK_FILE = "img_data_pack.npy"
# 学習したモデルを格納するファイル
CNN_MODEL_FILE = "img_data-model.hdf5"
# 画像分析に使用するモデルファイル（複数指定可能）
CNN_MODEL_FILES = ["img_data-model.hdf5"]
#学習のバッチサイズ
CNN_BATCH = 64
#学習の繰り返し回数
CNN_EPOCH = 10
# 分類対象のラベル
ADULT_LABEL = ['true','false','possible']
CATEGORIES_LABEL = ["illust", "photo", "text", "calendar", "cover","placard", "manga","capture","icon","craft"]
#LABEL_NUM = len(ADULT_LABEL+CATEGORIES_LABEL)
LABEL_NUM = len(CATEGORIES_LABEL)

GCV_ADULT_LABEL = ['UNKNOWN','VERY_UNLIKELY','UNLIKELY','POSSIBLE', 'LIKELY', 'VERY_LIKELY']
GCV_CATEGORIES_LABEL = ['art','illustration','cartoon','anime','comics','drawing','font','comic book','sketch','brand']
GCV_LABEL_NUM = len(GCV_ADULT_LABEL+GCV_CATEGORIES_LABEL)
#採用する教師データの閾値
SCORE_UPPER = 0.8