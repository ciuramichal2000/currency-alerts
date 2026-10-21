import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fxalert import Alerts  # noqa: E402


class Rates:
    def __init__(self, **r):
        self.r, self.calls = r, []

    def __call__(self, code):
        self.calls.append(code)
        return self.r[code]


def test_alert_fires_once_when_crossing_and_again_only_after_reset():
    f = Rates(EUR=4.30)
    a = Alerts(fetch=f)
    a.add_rule("eur", "above", 4.35)
    assert a.check() == []
    f.r["EUR"] = 4.40
    assert [x["rate"] for x in a.check()] == [4.40]
    f.r["EUR"] = 4.45
    assert a.check() == []                       # still above: no repeat
    f.r["EUR"] = 4.30
    assert a.check() == []                       # condition cleared
    f.r["EUR"] = 4.50
    assert len(a.check()) == 1                   # crossed again


def test_below_rule_and_invalid_operator():
    f = Rates(USD=3.9)
    a = Alerts(fetch=f)
    a.add_rule("USD", "below", 4.0)
    assert a.check()[0]["code"] == "USD"
    with pytest.raises(ValueError):
        a.add_rule("USD", "equal", 4.0)


def test_each_currency_is_fetched_once_per_check_even_with_several_rules():
    f = Rates(EUR=4.4)
    a = Alerts(fetch=f)
    a.add_rule("EUR", "above", 4.3)
    a.add_rule("EUR", "above", 4.35)
    a.add_rule("EUR", "below", 4.0)
    assert len(a.check()) == 2 and f.calls == ["EUR"]


def test_history_and_stats():
    f = Rates(EUR=4.0)
    t = iter(range(100))
    a = Alerts(fetch=f, clock=lambda: float(next(t)))
    a.add_rule("EUR", "above", 9)
    for v in (4.0, 4.2, 4.4):
        f.r["EUR"] = v
        a.check()
    assert [h["rate"] for h in a.history("EUR")] == [4.4, 4.2, 4.0]
    assert a.stats("EUR") == {"min": 4.0, "max": 4.4, "avg": 4.2, "n": 3} and a.stats("GBP") is None
