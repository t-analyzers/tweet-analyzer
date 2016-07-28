#!/bin/bash -l

export LC_LANG=ja_JP.UTF-8
export LANG=ja_JP.UTF-8

cd /Users/hitoshi/developer/tweet-analyzer-t/analyzer/
#echo $PATH > ../logs/env.log
/Users/hitoshi/.pyenv/versions/anaconda3-4.0.0/bin/python command.py a &> ../logs/archive.log
/Users/hitoshi/.pyenv/versions/anaconda3-4.0.0/bin/python feature_words_extractor.py &> ../logs/feature_words_extractor.log