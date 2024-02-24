from logzero import logger, logfile
from toolkit.fileutils import Fileutils
from toolkit.telegram import Telegram
from datetime import date

logfile(f"logs/halo-hash-{str(date.today())}.log")
SECDIR = "../../"
STGY = "strategies/"
FUTL = Fileutils()
CONFIG = FUTL.get_lst_fm_yml(SECDIR + "halo-hash.yml")
CRED = CONFIG["finvasia"]
CRED_ZERODHA = CONFIG["zerodha"]
TGRAM = Telegram(**CONFIG["telegram"])

if __name__ == "__main__":
    TGRAM.send_msg("testing")
