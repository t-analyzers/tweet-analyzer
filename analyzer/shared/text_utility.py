import re

# coding=utf-8
# write code...

TWITTER_ACCOUNT_PATTERN = r"@(.+?)\s"
URL_PATTERN = r"http(.+?)($|\s)"
NETWORKPRINT_ID_PATTERN = r"[A-Z0-9]{10}"
NPS_ID_PATTERN = r"[A-Z0-9]{8}"
HASHTAG_PATTERN = r"#(.+?)($|\s)"


def get_text_eliminated_some_pattern_words(text):
    """
    twitter accountとURLを文字列から消す
    :param text: 対象の文字列
    :return: 削除後の文字列
    """
    tmp = text
    for pattern in [TWITTER_ACCOUNT_PATTERN, URL_PATTERN, NETWORKPRINT_ID_PATTERN, NPS_ID_PATTERN, HASHTAG_PATTERN]:
        tmp = get_eliminated_text(pattern, tmp)
    return tmp


def get_nps_printid(text):
    """
    文字列にNPSの予約番号が含まれている場合、その予約番号を返す。含まれていない場合は空のリストを返す。
    :param text: 対象の文字列
    :return: 予約番号のリスト
    """
    # Network Printの番号は10桁なので事前に削除する。
    tmp = get_eliminated_text(NETWORKPRINT_ID_PATTERN, text)
    return [match.group() for match in re.finditer(NPS_ID_PATTERN, tmp, re.MULTILINE)]


def get_eliminated_text(pattern, text):
    """
    patternで指定した正規表現パターンの文字列を消す
    :param pattern: 正規表現
    :param text: 対象の文字列
    :return: 削除後の文字列
    """
    tmp = text
    for match in re.finditer(pattern, text, re.MULTILINE):
        tmp = tmp.replace(match.group(), '')
    return tmp
