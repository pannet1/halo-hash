from logzero import logger, logfile
from toolkit.fileutils import Fileutils
from toolkit.telegram import Telegram
from datetime import date

FUTL = Fileutils()
SECDIR = "../../"
S_LOG = f"{SECDIR}logs/halo-hash-{str(date.today())}.log"
if FUTL.is_file_not_2day(S_LOG):
    print(f"log file {S_LOG} created")
logfile(S_LOG)
STGY = "strategies/"
CONFIG = FUTL.get_lst_fm_yml(SECDIR + "halo-hash.yml")
CRED = CONFIG["finvasia"]
CRED_ZERODHA = CONFIG["zerodha"]
CRED_TELEGRAM = CONFIG["telegram"]
TGRAM = Telegram(CRED_TELEGRAM['api_key'], CRED_TELEGRAM['chat_id'])
TGRAM.send_msg("Starting up...Happy Trading !")
