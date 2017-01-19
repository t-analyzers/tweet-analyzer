# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 22:37:43 2017

image_analyzer.py用の設定ファイル

@author: hitoshi
"""

## mongodbの設定
DB_HOST = "localhost"
#DB_HOST = "192.168.11.3"
DB_PORT = 27017
DB_DB_NAME = "twitter-archive"
DB_TWEETS_COLLECTION_NAME = "tweets"
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
#学習用に画像とラベルの一式をまとめたファイル
LEARNING_PACK_FILE = "img_data_pack.npy"
#学習したモデルを格納するファイル
CNN_MODEL_FILE = "img_data-model.hdf5"
# 分類対象のラベル
adult_class = ['UNKNOWN','VERY_UNLIKELY','UNLIKELY','POSSIBLE', 'LIKELY', 'VERY_LIKELY']
categories = ['art','illustration','cartoon','anime','comics','drawing','font','comic book','sketch','brand']
label_num = len(adult_class+categories)
image_size = 128
