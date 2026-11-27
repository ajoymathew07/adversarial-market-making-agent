from mm.types import Side


def test_buy_has_positive_sign_and_sell_negative():
    assert Side.BUY.sign == 1
    assert Side.SELL.sign == -1


def test_opposite_swaps_sides():
    assert Side.BUY.opposite is Side.SELL
    assert Side.SELL.opposite is Side.BUY
