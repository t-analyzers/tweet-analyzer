import smtplib
from email.mime.text import MIMEText

# coding: UTF-8
# write code...


def send_mail(from_address, to_address):
    def receive_func(func):
        import functools

        @functools.wraps(func)
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
