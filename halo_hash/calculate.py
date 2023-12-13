def entry_quantity(**sym_config):
    print(f"calculate{sym_config}")
    risk_per_trade = int(sym_config["Risk per trade"]) #10 perc 
    lot_size = int(sym_config["lot_size"]) #1 
    stop_loss = sym_config["stop_loss"] # 10 points
    quantity = 0
    # calc capital available for this trade
    capital_allocated = int(sym_config["capital_in_thousand"]) * 1_00_0 / 100 * risk_per_trade # 900
    # calculate allowed quantity for the risk on hand
    allowable_quantity_as_per_risk = capital_allocated / stop_loss  # 90
    # find the nearest lot size
    rounded_lot = int(allowable_quantity_as_per_risk /  lot_size)  * lot_size # 90 
    if rounded_lot >= 2:
        quantity = int(rounded_lot / 2) * 2
    return quantity

if __name__ == "__main__":
    kwargs = { 
     'symbol': 'JIOFIN',
     'capital_in_thousand': '9', 
     'Risk per trade': '10',
     'Margin required': '1', 
     'lot_size': '1', 
    'stop_loss': 10
    }
    quantity = entry_quantity(**kwargs)
    print(f"{quantity}")

