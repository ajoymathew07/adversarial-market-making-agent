"""Unit tests for account accounting and unit conversion."""

import pytest

from mm.engine import Account, Fill, Side, price_to_ticks, ticks_to_price


def make_fill(taker_side: Side, price: int = 10000, size: int = 3) -> Fill:
    return Fill(
        taker_owner="bot",
        maker_owner="mm",
        maker_order_id=1,
        taker_side=taker_side,
        price=price,
        size=size,
        taker_tag="noise",
    )


def test_taker_buy_increases_taker_position_and_spends_cash():
    account = Account()
    account.apply_fill(make_fill(Side.BUY), as_owner="bot")
    assert (account.position, account.cash) == (3, -30000)


def test_maker_takes_opposite_side_of_taker():
    account = Account()
    account.apply_fill(make_fill(Side.BUY), as_owner="mm")
    assert (account.position, account.cash) == (-3, 30000)


def test_fee_per_lot_is_subtracted_from_cash_on_both_sides():
    buyer, seller = Account(fee_per_lot=2), Account(fee_per_lot=2)
    fill = make_fill(Side.BUY)
    buyer.apply_fill(fill, as_owner="bot")
    seller.apply_fill(fill, as_owner="mm")
    assert buyer.cash == -30000 - 6
    assert seller.cash == 30000 - 6


def test_apply_fill_rejects_owner_not_in_fill():
    with pytest.raises(ValueError):
        Account().apply_fill(make_fill(Side.BUY), as_owner="stranger")


def test_mark_to_values_position_at_given_price():
    account = Account()
    account.apply_fill(make_fill(Side.SELL, price=10000, size=2), as_owner="mm")
    assert account.mark_to(10010.5) == pytest.approx(-20000 + 2 * 10010.5)


def test_reconciles_after_fills_and_detects_tampering():
    account = Account(fee_per_lot=1)
    account.apply_fill(make_fill(Side.BUY), as_owner="mm")
    account.apply_fill(make_fill(Side.SELL, price=9990), as_owner="mm")
    assert account.reconciles()
    account.cash += 1
    assert not account.reconciles()


def test_ticks_convert_to_price_per_100_face_value():
    assert ticks_to_price(10000, 0.01) == pytest.approx(100.0)
    assert price_to_ticks(100.0, 0.01) == 10000


def test_price_to_ticks_rounds_to_nearest_tick():
    assert price_to_ticks(100.00999, 0.01) == 10001
    assert price_to_ticks(100.004, 0.01) == 10000
    assert price_to_ticks(100 + 1 / 32, 1 / 32) == 3201


def test_reconciles_detects_tampering_after_many_checked_fills():
    account = Account(fee_per_lot=1)
    for i in range(200):
        account.apply_fill(make_fill(Side.BUY if i % 2 else Side.SELL), as_owner="mm")
        assert account.reconciles()
    account.position += 1
    assert not account.reconciles()
    account.position -= 1
    account.cash -= 1
    assert not account.reconciles()


def test_reconciles_twice_without_new_fills_does_not_double_count():
    account = Account()
    account.apply_fill(make_fill(Side.BUY), as_owner="mm")
    assert account.reconciles()
    assert account.reconciles()
    account.apply_fill(make_fill(Side.SELL), as_owner="mm")
    assert account.reconciles()
