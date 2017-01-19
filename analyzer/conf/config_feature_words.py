# coding=utf-8
# for feature_word_extractor.py

# mongodb
HOST = "localhost"
PORT = 27017
DB_NAME = "twitter-archive"
COLLECTION_NAME = "tweets"

# twitter
CONSUMER_KEY = ""
CONSUMER_SECRET = ""
ACCESS_TOKEN_KEY = ""
ACCESS_TOKEN_SECRET = ""

#分析するデータの日数
ANALYZE_DAYS = 7
#抽出単語数
EXTRACT_FEATURE_WORDS_MAX = 10
#TF-IDFパラメータ：　除外する合計出現回数
TFIDF_EXCLUDE_APPEARANCE = 5

#出力先のフォルダのパス
OUTPUT_FOLDER_PATH = "../out/"

# 日本語フォントのパス
# OS Xなら/Library/Fonts, /System/Library/Fonts, ~/Library/Fontsあたりにあるはず。
# EX: "/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"
JAPANESE_FONT_PATH = ""
