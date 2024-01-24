def entry_quantity(**calc):
    # calc capital available for this trade
    caps = int(calc["capital_in_thousand"]) * 1_00_0  # 5 Lakhs
    # risk in rupees
    risk_in_rupees = float(calc["Risk per trade"]) / 100 * caps  # 10000
    # calculate stop loss
    stop_loss = calc["ltp"] - calc["last_10_candles"] \
        if calc["side"] == "B" else calc["last_10_candles"] - calc["ltp"]
    lot_size = int(calc["lot_size"])
    # calculate quantity from risk and stop
    qty_on_risk = risk_in_rupees / stop_loss  # 1000
    # calculate quantity from capital and ltp
    qty_on_capital = caps / calc["ltp"]  # 1000
    # minimum of the quantity
    quantity = min(int(qty_on_risk), int(qty_on_capital))
    # find the nearest lot size
    rounded_lot = int(quantity /
                      lot_size) * lot_size  # 90
    if rounded_lot >= 2:
        quantity = int(rounded_lot / 2) * 2
    calc["qty_on_capital"] = qty_on_capital
    calc["qty_on_risk"] = qty_on_risk
    calc["quantity"] = quantity
    calc["stop_loss"] = stop_loss
    print(f"{calc=}")
    return quantity, stop_loss


if __name__ == "__main__":
    kwargs = {
        'capital_in_thousand': '500',
        'Risk per trade': '2',
        'side': 'B',
        'ltp': 100,
        'last_10_candles': 90,
        'lot_size': '1',
    }
    quantity, stop_loss = entry_quantity(**kwargs)
    print(f"{quantity=}, {stop_loss=}")
