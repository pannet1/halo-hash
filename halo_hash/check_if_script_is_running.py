import psutil
from constants import TGRAM

for process in psutil.process_iter():
    if process.cmdline() == ['python', 'main_telegram.py']:
        TGRAM.send_msg("Good Morning, The script has started running!")
    else:
        TGRAM.send_msg("Good Morning, The script has not started today, please check!")

