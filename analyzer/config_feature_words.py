# coding=utf-8
# for feature_word_extractor.py

# mongodb
HOST = "localhost"
PORT = 27017
DB_NAME = "twitter-archive"
COLLECTION_NAME = "tweets"

# twitter
CONSUMER_KEY = " WN0jeKmrvLFIBYShJpKVrvLpE"
CONSUMER_SECRET = "LkOfgVHsOBZ9jSUgUMEXna3Dfapl7nJxmtTu5jIfG38kOr8R4M"
ACCESS_TOKEN_KEY = "615963673-vS0rtz54V4UxMeeWLq6EGi3vAO3fuN4cQUBfVHLe"
ACCESS_TOKEN_SECRET = "sgUYRV7o9nD3dr4PzZ7wYc14n9BNpqzCUtqNjA7gKKNZP"

#分析するデータの日数
ANALYZE_DAYS = 7
#抽出単語数
EXTRACT_FEATURE_WORDS_MAX = 10
#TF-IDFパラメータ：　除外する合計出現回数
TFIDF_EXCLUDE_APPEARANCE = 5

#出力先のフォルダのパス
OUTPUT_FOLDER_PATH = "/Users/hitoshi/Dropbox/Public/tweet-analyzer/data/"

# 日本語フォントのパス
# OS Xなら/Library/Fonts, /System/Library/Fonts, ~/Library/Fontsあたりにあるはず。
# EX: "/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"
JAPANESE_FONT_PATH = "/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"
