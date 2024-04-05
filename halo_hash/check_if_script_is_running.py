import psutil
from constants import TGRAM

for process in psutil.process_iter():
    if process.cmdline() == ['python3', 'main_telegram.py']:
        TGRAM.send_msg("Good Morning, The script has started running!")
        break
else:
    TGRAM.send_msg("Good Morning, The script has not started today, please check!")

