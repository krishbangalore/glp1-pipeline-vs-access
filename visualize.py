"""
GLP-1 Pipeline vs. Accessibility — Visualizations
Creates 3 charts saved to figures/
"""

import sqlite3
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import matplotlib.dates
from collections import defaultdict
import os
from datetime import date

from build_db import DB, LAST_YEAR, PULL_DATE
FIGURES = "figures"
os.makedirs(FIGURES, exist_ok=True)

PALETTE = {
    "Phase 1": "#a8c8e8",
    "Phase 2": "#5b9bd5",
    "Phase 3": "#1f5fa6",
    "Phase 4": "#0d3b66",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 150,
})


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def year_pos(d):
    """Map a date onto a yearly bar axis where year Y spans [Y-0.5, Y+0.5]."""
    return d.year - 0.5 + (d.timetuple().tm_yday - 1) / 365.0


# ── Chart 1: Trial pipeline growth by year (stacked bar by phase) ───────────
def chart_pipeline_growth():
    rows = load_csv("data/processed/q1_pipeline_growth.csv")

    years = sorted(set(int(r["start_year"]) for r in rows))
    phases = ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]
    data = {ph: [] for ph in phases}

    for year in years:
        year_data = {r["phase"]: int(r["trial_count"])
                     for r in rows if int(r["start_year"]) == year}
        for ph in phases:
            data[ph].append(year_data.get(ph, 0))

    fig, ax = plt.subplots(figsize=(12, 6))
    bottoms = [0] * len(years)
    for ph in phases:
        bars = ax.bar(years, data[ph], bottom=bottoms,
                      label=ph, color=PALETTE[ph], width=0.75, edgecolor="white", linewidth=0.5)
        # LAST_YEAR is a partial year — hatch it so it doesn't read as a full-year count
        for bar, yr in zip(bars, years):
            if yr == LAST_YEAR:
                bar.set_hatch("///")
                bar.set_alpha(0.6)
        bottoms = [b + v for b, v in zip(bottoms, data[ph])]

    # Shade the semaglutide shortage (Mar 2022 → Feb 21 2025). Each bar spans
    # its calendar year as [year - 0.5, year + 0.5].
    ax.axvspan(year_pos(date(2022, 3, 1)), year_pos(date(2025, 2, 21)),
               alpha=0.08, color="#e8a020", zorder=0)
    ax.text(2023.1, max(bottoms) * 0.97, "Semaglutide on FDA shortage list\n(Mar 2022 – Feb 2025)",
            ha="center", va="top", fontsize=8, color="#b07010", style="italic")
    ax.text(LAST_YEAR, bottoms[-1] + max(bottoms) * 0.01, f"partial\n(to {PULL_DATE})",
            ha="center", va="bottom", fontsize=7, color="#555")

    ax.set_xlabel("Trial Start Year", fontsize=11)
    ax.set_ylabel("Trials started", fontsize=11)
    ax.set_title(f"GLP-1 Interventional Trial Starts by Phase (2005–{LAST_YEAR}; {LAST_YEAR} partial)",
                 fontsize=13, fontweight="bold", pad=12)
    ax.legend(title="Phase", loc="upper left", framealpha=0.8)
    ax.set_xlim(2004.5, LAST_YEAR + 0.5)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(2))

    fig.tight_layout()
    fig.savefig(f"{FIGURES}/fig1_pipeline_growth.png")
    plt.close(fig)
    print("  Saved fig1_pipeline_growth.png")


# ── Chart 2: Sponsor landscape (horizontal bar, top 10) ─────────────────────
def chart_sponsor_landscape():
    rows = load_csv("data/processed/q2_sponsor_landscape.csv")
    rows = rows[:10]

    sponsors = [r["lead_sponsor_name"][:35] for r in rows]
    totals = [int(r["total_trials"]) for r in rows]
    ph3 = [int(r["phase3_trials"]) for r in rows]
    other = [t - p for t, p in zip(totals, ph3)]

    fig, ax = plt.subplots(figsize=(10, 6))
    y = range(len(sponsors))
    ax.barh(y, other, label="Phase 1/2/4", color="#a8c8e8")
    ax.barh(y, ph3, left=other, label="Phase 3", color="#1f5fa6")
    ax.set_yticks(list(y))
    ax.set_yticklabels(sponsors, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Trial Count", fontsize=11)
    ax.set_title(f"Top Sponsors in GLP-1 Interventional Trials (starts through {LAST_YEAR})",
                 fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="lower right")

    for i, (t, p3) in enumerate(zip(totals, ph3)):
        ax.text(t + 1, i, f"{t}  ({p3} Ph3)", va="center", fontsize=8.5)

    fig.tight_layout()
    fig.savefig(f"{FIGURES}/fig2_sponsor_landscape.png")
    plt.close(fig)
    print("  Saved fig2_sponsor_landscape.png")


# ── Chart 3: The centerpiece timeline chart ──────────────────────────────────
def chart_access_timeline():
    """
    Event timeline built only from the cited, hand-entered tables:
    shortage windows + wind-downs (shortage_status), FDA warning-letter
    batches (enforcement_events), Lilly price/access events and FDA policy
    (policy_events). Bottom panel: interventional trial starts per year.
    """
    conn = sqlite3.connect(DB)
    shortages = conn.execute("""
        SELECT drug_name, shortage_start, shortage_end, wind_down_503b_end
        FROM shortage_status ORDER BY shortage_start
    """).fetchall()
    batches = conn.execute("""
        SELECT letter_date, letter_count, count_source FROM enforcement_events
        ORDER BY letter_date
    """).fetchall()
    events = conn.execute("""
        SELECT event_date, event_type, description FROM policy_events
        WHERE event_type IN ('LILLY_ACCESS', 'LILLY_PRICE', 'FDA_PROPOSED_RULE')
        ORDER BY event_date
    """).fetchall()
    trial_rows = conn.execute(f"""
        SELECT start_year, COUNT(DISTINCT nct_id) AS cnt
        FROM trials_clean
        WHERE start_year BETWEEN 2020 AND {LAST_YEAR}
        GROUP BY start_year
    """).fetchall()
    conn.close()

    d = date.fromisoformat
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9.5),
                                   gridspec_kw={"height_ratios": [3, 1.6]})

    # ── Top panel: shortage bands (left axis rows) ──────────────────────────
    lanes = {name: i for i, (name, *_rest) in enumerate(shortages)}
    for name, start, end, wd_end in shortages:
        y = lanes[name]
        ax1.barh(y, (d(end) - d(start)).days, left=d(start), height=0.5,
                 color="#27ae60", alpha=0.45)
        ax1.barh(y, (d(wd_end) - d(end)).days, left=d(end), height=0.5,
                 color="#f39c12", alpha=0.45)
        ax1.text(d(start), y + 0.33, f"{name}: {start[:7]} → {end}",
                 fontsize=8, va="bottom")

    ax1.set_yticks(list(lanes.values()))
    ax1.set_yticklabels([n.capitalize() for n in lanes], fontsize=9)
    ax1.set_ylim(-0.6, len(lanes) + 2.4)

    # ── Warning-letter batches (right axis, stems) ──────────────────────────
    ax1b = ax1.twinx()
    for ld, n, basis in batches:
        firm = not basis.startswith("secondary")
        ax1b.vlines(d(ld), 0, n, color="#c0392b", linewidth=3, alpha=0.85 if firm else 0.45,
                    linestyle="-" if firm else "--")
        ax1b.plot(d(ld), n, "o", color="#c0392b", alpha=0.85 if firm else 0.45)
        label = f"~{n}" if basis.startswith("approx") else f"{n}" + ("*" if not firm else "")
        ax1b.text(d(ld), n + 2, label, ha="center", fontsize=8, color="#c0392b")
    ax1b.set_ylim(0, 95)
    ax1b.set_ylabel("FDA warning letters per batch", fontsize=9, color="#c0392b")
    ax1b.spines["right"].set_visible(True)
    ax1b.grid(False)

    # ── Lilly + FDA policy markers ──────────────────────────────────────────
    short_labels = {
        "2024-01-04": "LillyDirect\nlaunches",
        "2024-08-27": "Zepbound vials\n\\$399 / \\$549",
        "2025-02-25": "More vial doses;\n\\$349–\\$499",
        "2025-12-01": "Vials cut to\n\\$299–\\$449",
        "2026-04-30": "FDA proposes\n503B exclusion",
    }
    for i, (ed, etype, _desc) in enumerate(events):
        color = "#2c3e50" if etype == "FDA_PROPOSED_RULE" else "#8e44ad"
        ax1.axvline(d(ed), color=color, linestyle=":" if etype == "FDA_PROPOSED_RULE" else "--",
                    linewidth=1.3, alpha=0.8)
        ax1.text(d(ed), len(lanes) + 1.9 - (i % 2) * 0.75, short_labels.get(ed, ed),
                 fontsize=7.5, color=color, ha="left", va="top")

    ax1.set_xlim(d("2022-01-01"), d(PULL_DATE))
    ax1.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=(1, 7)))
    ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m"))
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    ax1.set_title("Shortage Windows, FDA Enforcement and Lilly Pricing (cited events only)",
                  fontsize=12, fontweight="bold", pad=10)

    legend_patches = [
        mpatches.Patch(color="#27ae60", alpha=0.45, label="On FDA shortage list"),
        mpatches.Patch(color="#f39c12", alpha=0.45, label="Post-resolution wind-down (to 503B deadline)"),
        mpatches.Patch(color="#c0392b", alpha=0.85, label="FDA warning-letter batch (* = secondary-source count)"),
        mpatches.Patch(color="#8e44ad", alpha=0.8, label="Lilly access / price event"),
        mpatches.Patch(color="#2c3e50", alpha=0.8, label="FDA policy"),
    ]
    ax1.legend(handles=legend_patches, fontsize=7.5, loc="upper left", framealpha=0.9)

    # ── Bottom panel: interventional trial starts per year ──────────────────
    trial_years = [r[0] for r in trial_rows]
    trial_counts = [r[1] for r in trial_rows]
    colors = ["#5b9bd5" if y < 2022 else "#27ae60" if y <= 2024 else "#e67e22"
              for y in trial_years]

    bars = ax2.bar(trial_years, trial_counts, color=colors, width=0.65, edgecolor="white")
    for bar, yr in zip(bars, trial_years):
        if yr == LAST_YEAR:
            bar.set_hatch("///")
            bar.set_alpha(0.6)
    ax2.set_ylabel("Trials started", fontsize=10)
    ax2.set_xlabel("Start year", fontsize=10)
    ax2.set_title(f"GLP-1 Interventional Trial Starts by Year (2020–{LAST_YEAR}; "
                  f"{LAST_YEAR} partial, through {PULL_DATE})", fontsize=11, pad=8)
    for y, ct in zip(trial_years, trial_counts):
        ax2.text(y, ct + 0.5, f"{ct}*" if y == LAST_YEAR else str(ct), ha="center", fontsize=9)

    fig.tight_layout(pad=2.5)
    fig.savefig(f"{FIGURES}/fig3_access_timeline.png", bbox_inches="tight")
    plt.close(fig)
    print("  Saved fig3_access_timeline.png")


if __name__ == "__main__":
    print("Building visualizations...")
    chart_pipeline_growth()
    chart_sponsor_landscape()
    chart_access_timeline()
    print("\n✓ All figures saved to figures/")
