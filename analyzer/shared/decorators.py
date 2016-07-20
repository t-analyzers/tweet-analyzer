import smtplib
from email.mime.text import MIMEText
from functools import wraps

# coding: UTF-8
# write code...


def send_mail(from_address, to_address):
    """
    関数の呼び出し終了後にメール送信するデコレータ
    :param from_address: 送信者アドレス
    :param to_address: 宛先アドレス
    """
    def receive_func(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Create mail
            text = "Process \"{0}\" is finished!!\n".format(func.__name__)
            text += "( Program file : {0} )\n".format(__file__)

            msg = MIMEText(text)
            msg['Subject'] = "Process is finished!!"
            msg['From'] = from_address
            msg['To'] = to_address

            # Send mail
            s = smtplib.SMTP()
            s.connect()
            s.sendmail(from_address, [to_address], msg.as_string())
            s.close()

            # Debug print
            print("Debug: Send mail to \"{0}\" from \"{1}\".".format(to_address, from_address))

            return result
        return wrapper
    return receive_func


def trace():
    """
    関数の呼び出し前と呼び出し後に関数名をコンソール出力するデコレータ
    """
    def receive_func(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                print("[TRACE]: {0} start".format(func.__name__))
                result = func(*args, **kwargs)
                print("[TRACE]: {0} finished".format(func.__name__))
                return result
            except Exception as e:
                print(str(e))
                raise
        return wrapper
    return receive_func
