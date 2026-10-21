# currency-alerts

Rules such as "EUR above 4.35 PLN" checked against the official NBP rates. An alert fires **once** when the condition becomes true and again only after it has been false in between, so you are not told every hour about the same thing. Each currency is fetched once per check even with several rules; every rate is stored in SQLite with min/max/average.

The rate source is injectable, so the tests run without a network (`python -m pytest`). The live source is `nbp_fetch`. Pure Python standard library; built with AI coding assistance.
