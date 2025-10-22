"""Generate an SVG plot comparing ABTC and BTC price trendlines.

The script reads a CSV file containing ABTC and BTC price history, computes
linear trendlines together with the daily percentage fluctuation rate, and
renders everything onto a single SVG chart. The output SVG contains two y
axes – prices on the left and percentage fluctuation on the right – so the
requested trendlines and fluctuation curves appear together.

The implementation uses only the Python standard library so it can run in
minimal environments without third-party plotting packages.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "abtc_btc_prices.csv"
DEFAULT_OUTPUT_PATH = Path.cwd() / "abtc_btc_trend.svg"
ASSETS = ("ABTC", "BTC")
PRICE_COLORS: Dict[str, str] = {"ABTC": "#2ca02c", "BTC": "#1f77b4"}
TRENDLINE_COLORS: Dict[str, str] = {"ABTC": "#98df8a", "BTC": "#aec7e8"}
FLUCTUATION_COLORS: Dict[str, str] = {"ABTC": "#d62728", "BTC": "#ff7f0e"}


@dataclass
class PriceSeries:
    dates: List[datetime]
    prices: Dict[str, List[float]]


def load_price_data(csv_path: Path) -> PriceSeries:
    """Return ordered price data parsed from ``csv_path``."""

    dates: List[datetime] = []
    prices: Dict[str, List[float]] = {asset: [] for asset in ASSETS}

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = set(ASSETS).difference(reader.fieldnames or [])
        if "date" not in (reader.fieldnames or []):
            raise ValueError("CSV must contain a 'date' column")
        if missing:
            raise ValueError(
                "CSV is missing expected asset columns: " + ", ".join(sorted(missing))
            )
        for row in reader:
            date = datetime.fromisoformat(row["date"])  # type: ignore[arg-type]
            dates.append(date)
            for asset in ASSETS:
                value = float(row[asset])
                prices[asset].append(value)

    if not dates:
        raise ValueError("No rows found in price CSV")

    return PriceSeries(dates=dates, prices=prices)


def compute_trendline(values: Sequence[float]) -> List[float]:
    """Return the linear regression trendline for ``values``."""

    n = len(values)
    if n == 0:
        return []

    xs = list(range(n))
    sum_x = sum(xs)
    sum_y = sum(values)
    sum_xx = sum(x * x for x in xs)
    sum_xy = sum(x * y for x, y in zip(xs, values))
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        slope = 0.0
    else:
        slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return [slope * x + intercept for x in xs]


def compute_fluctuation(values: Sequence[float]) -> List[float]:
    """Return the day-over-day percentage change for ``values``."""

    if not values:
        return []
    result = [0.0]
    for prev, curr in zip(values, values[1:]):
        if prev == 0:
            result.append(0.0)
        else:
            result.append(((curr - prev) / prev) * 100.0)
    return result


def compute_relative_change(values: Sequence[float]) -> List[float]:
    """Return the percentage change from the first value in ``values``."""

    if not values:
        return []
    baseline = values[0]
    if baseline == 0:
        return [0.0 for _ in values]
    return [((value - baseline) / baseline) * 100.0 for value in values]


def _linspace(start: float, stop: float, count: int) -> List[float]:
    if count == 1:
        return [start]
    step = (stop - start) / (count - 1)
    return [start + step * i for i in range(count)]


def _format_currency(value: float) -> str:
    if value >= 1000 or value <= -1000:
        return f"${value:,.0f}"
    return f"${value:,.2f}"


def _format_percent(value: float) -> str:
    return f"{value:.1f}%"


def _svg_polyline(points: Iterable[tuple[float, float]], color: str, width: float = 2.0, dash: str | None = None) -> str:
    attrs = [
        "fill='none'",
        f"stroke='{color}'",
        f"stroke-width='{width}'",
    ]
    if dash:
        attrs.append(f"stroke-dasharray='{dash}'")
    coord_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f"<polyline {' '.join(attrs)} points='{coord_str}' />"


def _svg_text(x: float, y: float, text: str, anchor: str = "middle", size: int = 14) -> str:
    return (
        f"<text x='{x:.2f}' y='{y:.2f}' text-anchor='{anchor}' "
        f"font-family='Arial, sans-serif' font-size='{size}' fill='#333'>{text}</text>"
    )


def render_svg(series: PriceSeries, output_path: Path) -> None:
    """Render the ABTC/BTC price trends and fluctuations into ``output_path``."""

    width, height = 1000, 620
    margin_left, margin_right, margin_top, margin_bottom = 90, 110, 70, 80
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    count = len(series.dates)
    xs = _linspace(margin_left, margin_left + plot_width, count)

    relative_prices: Dict[str, List[float]] = {
        asset: compute_relative_change(values) for asset, values in series.prices.items()
    }
    rel_min = min(min(values) for values in relative_prices.values())
    rel_max = max(max(values) for values in relative_prices.values())
    rel_range = rel_max - rel_min if rel_max != rel_min else 1.0

    fluctuation: Dict[str, List[float]] = {}
    fluct_min, fluct_max = 0.0, 0.0
    for asset, values in series.prices.items():
        fluct = compute_fluctuation(values)
        fluctuation[asset] = fluct
        fluct_min = min(fluct_min, min(fluct))
        fluct_max = max(fluct_max, max(fluct))
    if fluct_min == fluct_max:
        fluct_min -= 1
        fluct_max += 1
    fluct_padding = (fluct_max - fluct_min) * 0.05
    fluct_min -= fluct_padding
    fluct_max += fluct_padding

    def price_y(value: float) -> float:
        normalized = (value - rel_min) / rel_range
        return margin_top + plot_height - normalized * plot_height

    def fluct_y(value: float) -> float:
        normalized = (value - fluct_min) / (fluct_max - fluct_min)
        return margin_top + plot_height - normalized * plot_height

    price_trendlines = {
        asset: compute_trendline(values) for asset, values in relative_prices.items()
    }

    svg_parts: List[str] = [
        "<?xml version='1.0' encoding='utf-8'?>",
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<rect width='100%' height='100%' fill='white'/>",
    ]

    # Draw grid lines based on cumulative percentage axis ticks
    price_ticks = 6
    for i in range(price_ticks):
        value = rel_min + (rel_range / (price_ticks - 1)) * i
        y = price_y(value)
        svg_parts.append(
            f"<line x1='{margin_left}' y1='{y:.2f}' x2='{margin_left + plot_width}' y2='{y:.2f}' "
            "stroke='#e0e0e0' stroke-dasharray='4 6' />"
        )
        svg_parts.append(_svg_text(margin_left - 10, y + 5, _format_percent(value), anchor="end"))

    # Axis lines
    bottom = margin_top + plot_height
    svg_parts.append(
        f"<line x1='{margin_left}' y1='{margin_top}' x2='{margin_left}' y2='{bottom}' stroke='#333' stroke-width='1.5'/>"
    )
    svg_parts.append(
        f"<line x1='{margin_left}' y1='{bottom}' x2='{margin_left + plot_width}' y2='{bottom}' stroke='#333' stroke-width='1.5'/>"
    )
    svg_parts.append(
        f"<line x1='{margin_left + plot_width}' y1='{margin_top}' x2='{margin_left + plot_width}' y2='{bottom}' stroke='#333' stroke-width='1.5'/>"
    )

    # Right axis labels for fluctuation
    fluct_ticks = 6
    for i in range(fluct_ticks):
        value = fluct_min + ((fluct_max - fluct_min) / (fluct_ticks - 1)) * i
        y = fluct_y(value)
        svg_parts.append(_svg_text(margin_left + plot_width + 10, y + 5, _format_percent(value), anchor="start"))

    # X-axis labels (every few dates)
    label_count = min(6, count)
    step = max(1, count // (label_count - 1)) if label_count > 1 else 1
    for idx in range(0, count, step):
        date_label = series.dates[idx].strftime("%b %d")
        svg_parts.append(_svg_text(xs[idx], bottom + 25, date_label, anchor="middle"))
    if (count - 1) % step != 0:
        svg_parts.append(_svg_text(xs[-1], bottom + 25, series.dates[-1].strftime("%b %d"), anchor="middle"))

    # Plot cumulative change series and trendlines
    for asset in ASSETS:
        price_points = list(zip(xs, (price_y(val) for val in relative_prices[asset])))
        svg_parts.append(_svg_polyline(price_points, PRICE_COLORS[asset], width=3.0))

        trend_points = list(zip(xs, (price_y(val) for val in price_trendlines[asset])))
        svg_parts.append(
            _svg_polyline(
                trend_points,
                TRENDLINE_COLORS[asset],
                width=2.0,
                dash="6 6",
            )
        )

    # Plot fluctuation lines
    for asset in ASSETS:
        fluct_points = list(zip(xs, (fluct_y(val) for val in fluctuation[asset])))
        svg_parts.append(
            _svg_polyline(
                fluct_points,
                FLUCTUATION_COLORS[asset],
                width=2.0,
                dash="2 6",
            )
        )

    # Titles and axis labels
    svg_parts.append(
        _svg_text(
            width / 2,
            margin_top - 25,
            "ABTC vs BTC % Change & Daily Fluctuations",
            size=22,
        )
    )
    svg_parts.append(_svg_text(width / 2, height - 25, "Date", size=16))
    svg_parts.append(
        _svg_text(margin_left - 60, margin_top - 30, "% Change", anchor="middle", size=16)
    )
    svg_parts.append(_svg_text(width - margin_right / 2, margin_top - 30, "Daily Change", anchor="middle", size=16))

    # Legend
    legend_x = margin_left + 20
    legend_y = margin_top + 20
    legend_spacing = 22
    legend_items = [
        ("ABTC % Change", PRICE_COLORS["ABTC"], None),
        ("ABTC Trendline", TRENDLINE_COLORS["ABTC"], "6 6"),
        ("ABTC Daily %", FLUCTUATION_COLORS["ABTC"], "2 6"),
        ("BTC % Change", PRICE_COLORS["BTC"], None),
        ("BTC Trendline", TRENDLINE_COLORS["BTC"], "6 6"),
        ("BTC Daily %", FLUCTUATION_COLORS["BTC"], "2 6"),
    ]
    for index, (label, color, dash) in enumerate(legend_items):
        y = legend_y + index * legend_spacing
        svg_parts.append(
            f"<line x1='{legend_x}' y1='{y:.2f}' x2='{legend_x + 28}' y2='{y:.2f}' "
            f"stroke='{color}' stroke-width='3'" + (f" stroke-dasharray='{dash}'" if dash else "") + "/>"
        )
        svg_parts.append(_svg_text(legend_x + 40, y + 5, label, anchor="start"))

    svg_parts.append("</svg>")

    output_path.write_text("\n".join(svg_parts), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot ABTC and BTC price trendlines with fluctuation rates (SVG output).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to the CSV file containing price data (default: data/abtc_btc_prices.csv).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to save the generated SVG plot (default: ./abtc_btc_trend.svg).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    series = load_price_data(args.csv)
    render_svg(series, args.output)
    print(f"SVG plot written to {args.output}")


if __name__ == "__main__":
    main()
