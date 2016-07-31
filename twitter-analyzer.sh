#!/bin/bash -l

export LC_LANG=ja_JP.UTF-8
export LANG=ja_JP.UTF-8

/usr/local/bin/mongod --config /usr/local/etc/mongod.conf &

cd $HOME/developer/tweet-analyzer-t/analyzer/
$HOME/.pyenv/versions/anaconda3-4.0.0/bin/python command.py a &> ../logs/archive.log
$HOME/.pyenv/versions/anaconda3-4.0.0/bin/python feature_words_extractor.py &> ../logs/feature_words_extractor.log

exit