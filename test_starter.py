
import asyncio
from decimal import Decimal

import pytest

from starter import recommend_price


def _offer(*, price, seller="PARTS", delivery_days=3):
    return {
        "seller": seller,
        "price": Decimal(price),
        "delivery_days": delivery_days,
    }


async def _failed_fetch():
    raise RuntimeError("Source unavailable")


async def _slow_fetch():
    await asyncio.sleep(1)


@pytest.mark.parametrize(
    ("offers", "current", "minimum", "expected", "decision"),
    [
        pytest.param(
            [
                _offer(price="4300.00", seller="myshop"),
                _offer(price="4800.00"),
                _offer(price="4700.00", delivery_days=8),
            ],
            "4900.00", "4500.00", "4728.00", "APPLY",
            id="normal",
        ),
        pytest.param(
            [_offer(price="100.01")],
            "100.00", "50.00", "98.50", "APPLY",
            id="round-down",
        ),
        pytest.param(
            [_offer(price="100.00")],
            "100.00", "99.00", "99.00", "APPLY",
            id="min-price",
        ),
        pytest.param(
            [
                _offer(price="100.00", seller="MYSHOP"),
                _offer(price="100.00", delivery_days=None),
                _offer(price="100.00", delivery_days=7),
                _offer(price="200.00", delivery_days=6),
            ],
            "200.00", "100.00", "197.00", "APPLY",
            id="filter-offers",
        ),
        pytest.param(
            [],
            "400.00", "450.00", "400.00", "HOLD",
            id="no-offers",
        ),
        pytest.param(
            [_offer(price="710.66")],
            "1000.00", "500.00", "700.00", "APPLY",
            id="exactly-minus-30",
        ),
        pytest.param(
            [_offer(price="710.65")],
            "1000.00", "500.00", "699.99", "REVIEW",
            id="more-than-minus-30",
        ),
        pytest.param(
            [_offer(price="1000.00")],
            "1000.00", "1300.00", "1300.00", "APPLY",
            id="exactly-plus-30",
        ),
        pytest.param(
            [_offer(price="1000.00")],
            "1000.00", "1300.01", "1300.01", "REVIEW",
            id="more-than-plus-30",
        ),
    ],
)
def test_recommend_price(offers, current, minimum, expected, decision):
    async def fetch_offers():
        return {"status": "success", "offers": offers}

    result = asyncio.run(
        recommend_price(
            fetch_offers,
            current_price=Decimal(current),
            min_price=Decimal(minimum),
        )
    )

    assert result["price"] == Decimal(expected)
    assert result["decision"] == decision
    assert isinstance(result["price"], Decimal)
    assert result["reason"]


@pytest.mark.parametrize("status", ["partial", "error"])
def test_source_status(status):
    async def fetch_offers():
        return {"status": status, "offers": []}

    result = asyncio.run(
        recommend_price(
            fetch_offers,
            current_price=Decimal("4900.00"),
            min_price=Decimal("4500.00"),
        )
    )

    assert result["price"] == Decimal("4900.00")
    assert result["decision"] == "HOLD"
    assert result["reason"]


@pytest.mark.parametrize(
    ("fetch_offers", "timeout_s"),
    [
        pytest.param(_failed_fetch, 2.0, id="exception"),
        pytest.param(_slow_fetch, 0.001, id="timeout"),
    ],
)
def test_source_failure(fetch_offers, timeout_s):
    result = asyncio.run(
        recommend_price(
            fetch_offers,
            current_price=Decimal("4900.00"),
            min_price=Decimal("4500.00"),
            timeout_s=timeout_s,
        )
    )

    assert result["price"] == Decimal("4900.00")
    assert result["decision"] == "HOLD"
    assert result["reason"]
