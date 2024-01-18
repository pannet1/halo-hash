from toolkit.logger import Logger
from toolkit.fileutils import Fileutils
from toolkit.telegram import Telegram

logging = Logger(30)
SECDIR = "../../"
STGY = "strategies/"
FUTL = Fileutils()
CONFIG = FUTL.get_lst_fm_yml(SECDIR + "halo-hash.yml")
CRED = CONFIG["finvasia"]
CRED_ZERODHA = CONFIG["zerodha"]
TGRAM = Telegram(**CONFIG["telegram"])

if __name__ == "__main__":
    TGRAM.send_msg("testing")
