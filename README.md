# jgcodex
This is my first test repo for Codex integration.

## Generating ABTC vs BTC Trendlines

Use the helper script in `scripts/plot_abtc_btc.py` to plot trendlines for
ABTC and BTC cumulative percentage changes (relative to the first date in the
dataset), along with their daily percentage fluctuation rates on a shared
chart. The repository ships with a sample dataset at
`data/abtc_btc_prices.csv`.

```bash
python scripts/plot_abtc_btc.py
```

By default the plot is saved as `abtc_btc_trend.svg` in the current working
directory. You can supply your own CSV data via the `--csv` flag and control
the output filename with `--output`.

The script intentionally relies only on the Python standard library so it can
run in restricted environments without external plotting dependencies. The
repository includes a pre-generated `abtc_btc_trend.svg` created from the
sample dataset so you can inspect the output without executing the script.
