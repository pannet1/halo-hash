from toolkit.fileutils import Fileutils
from omspy_brokers.finvasia import Finvasia


SECDIR = "../../"
FUTL = Fileutils()
CONFIG = FUTL.get_lst_fm_yml(SECDIR + "halo-hash.yml")
CRED = CONFIG["finvasia"]
BROKER = Finvasia
broker = BROKER(**CRED)
if broker.authenticate():
    print("login successful")
    print(broker.orders)

