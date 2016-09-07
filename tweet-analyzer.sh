#!/bin/bash -l

export LC_LANG=ja_JP.UTF-8
export LANG=ja_JP.UTF-8

/usr/local/bin/mongod --config /usr/local/etc/mongod.conf &

TODAY=`date '+%F'`
cd $HOME/developer/tweet-analyzer-t/analyzer/

#tweet取得
$HOME/.pyenv/versions/anaconda3-4.0.0/bin/python command.py a &> ../logs/archive_$TODAY.log
#教師データ作成
#$HOME/.pyenv/versions/anaconda3-4.0.0/bin/python create_learning_data_using_metadata.py &> ../logs/create_learning_data_using_metadata_$TODAY.log
#ツイートネガポジ判定
$HOME/.pyenv/versions/anaconda3-4.0.0/bin/python svm_scorer_using_metadata.py &> ../logs/svm_scorer_using_metadata_$TODAY.log
#ツイート分析結果出力
$HOME/.pyenv/versions/anaconda3-4.0.0/bin/python feature_words_extractor.py &> ../logs/feature_words_extractor_$TODAY.log


exit