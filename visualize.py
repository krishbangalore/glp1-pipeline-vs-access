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
from collections import defaultdict
import os

DB = "/tmp/glp1_analysis.db"
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
        bottoms = [b + v for b, v in zip(bottoms, data[ph])]

    # Shade the GLP-1 shortage period (approx 2022-mid-2025)
    ax.axvspan(2021.5, 2025.3, alpha=0.08, color="#e8a020", zorder=0)
    ax.text(2023.4, max(bottoms) * 0.97, "FDA shortage window\n(compounding legal)",
            ha="center", va="top", fontsize=8, color="#b07010", style="italic")

    ax.set_xlabel("Trial Start Year", fontsize=11)
    ax.set_ylabel("New Trials Registered", fontsize=11)
    ax.set_title("GLP-1 Peptide Drug Clinical Trial Pipeline Growth (2005–2026)",
                 fontsize=13, fontweight="bold", pad=12)
    ax.legend(title="Phase", loc="upper left", framealpha=0.8)
    ax.set_xlim(2004.5, 2026.5)
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
    ax.set_title("Top Sponsors in GLP-1 Peptide Drug Trials",
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
    Single timeline: shortage window (shaded) + warning letter volume
    + Lilly price cut events + new trial registrations
    """
    conn = sqlite3.connect(DB)

    # Monthly warning letters
    wl_rows = conn.execute("""
        SELECT SUBSTR(issue_date, 1, 7) AS month, COUNT(*) AS cnt
        FROM warning_letters
        WHERE issue_date >= '2023-01-01'
        GROUP BY month
        ORDER BY month
    """).fetchall()

    # Annual new trials for the overlay
    trial_rows = conn.execute("""
        SELECT start_year, COUNT(DISTINCT nct_id) AS cnt
        FROM trials_clean
        WHERE start_year BETWEEN 2020 AND 2026
        GROUP BY start_year
    """).fetchall()
    conn.close()

    months = [r[0] for r in wl_rows]
    counts = [r[1] for r in wl_rows]
    x_numeric = list(range(len(months)))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), sharex=False,
                                   gridspec_kw={"height_ratios": [3, 1.6]})

    # ── Top panel: warning letters timeline ─────────────────────────────────
    bars = ax1.bar(x_numeric, counts, color="#c0392b", alpha=0.75, width=0.8,
                   label="FDA warning letters (monthly)")

    # Shade shortage period (months in range 2022-03 to 2025-02)
    shade_start = next((i for i, m in enumerate(months) if m >= "2022-03"), None)
    shade_end_sem = next((i for i, m in enumerate(months) if m >= "2025-02"), len(months) - 1)
    shade_end_tirz = next((i for i, m in enumerate(months) if m >= "2024-10"), len(months) - 1)

    if shade_start is not None:
        ax1.axvspan(shade_start - 0.5, shade_end_tirz + 0.5,
                    alpha=0.10, color="#27ae60", zorder=0)
        ax1.axvspan(shade_end_tirz + 0.5, shade_end_sem + 0.5,
                    alpha=0.06, color="#f39c12", zorder=0)

    # Lilly price cut markers
    price_cut_months = {"2025-02": "Lilly cuts\nZepbound price\n$399/mo vial",
                        "2025-12": "Lilly cuts\nprice further;\nLillyDirect launch"}
    for pm, label in price_cut_months.items():
        idx = next((i for i, m in enumerate(months) if m == pm), None)
        if idx is not None:
            ax1.axvline(idx, color="#8e44ad", linestyle="--", linewidth=1.5, alpha=0.8)
            ax1.text(idx + 0.2, max(counts) * 0.88, label,
                     fontsize=7.5, color="#8e44ad", va="top")

    # FDA policy marker
    policy_month = "2026-04"
    idx = next((i for i, m in enumerate(months) if m == policy_month), None)
    if idx is not None:
        ax1.axvline(idx, color="#2c3e50", linestyle=":", linewidth=1.5, alpha=0.9)
        ax1.text(idx + 0.2, max(counts) * 0.60,
                 "FDA proposes 503B\npermanent exclusion",
                 fontsize=7.5, color="#2c3e50", va="top")

    # X-axis labels (every 3 months)
    tick_indices = [i for i, m in enumerate(months) if m.endswith(("-01", "-04", "-07", "-10"))]
    tick_labels = [months[i] for i in tick_indices]
    ax1.set_xticks(tick_indices)
    ax1.set_xticklabels(tick_labels, rotation=45, ha="right", fontsize=8)
    ax1.set_ylabel("Warning Letters Issued", fontsize=10)
    ax1.set_title("FDA Enforcement vs. Shortage Window: GLP-1 Compounding Crackdown (2023–2026)",
                  fontsize=12, fontweight="bold", pad=10)

    legend_patches = [
        mpatches.Patch(color="#27ae60", alpha=0.35, label="Shortage active (compounding legal)"),
        mpatches.Patch(color="#f39c12", alpha=0.35, label="Semaglutide shortage resolved (Oct 24–Feb 25)"),
        mpatches.Patch(color="#c0392b", alpha=0.75, label="FDA warning letters"),
        mpatches.Patch(color="#8e44ad", alpha=0.8, label="Eli Lilly price cuts"),
    ]
    ax1.legend(handles=legend_patches, fontsize=8, loc="upper left", framealpha=0.85)

    # ── Bottom panel: new trial registrations 2020-2026 ─────────────────────
    trial_years = [r[0] for r in trial_rows]
    trial_counts = [r[1] for r in trial_rows]
    colors = ["#5b9bd5" if y < 2022 else "#27ae60" if y <= 2024 else "#e67e22"
              for y in trial_years]

    ax2.bar(trial_years, trial_counts, color=colors, width=0.65, edgecolor="white")
    ax2.set_ylabel("New Trials Registered", fontsize=10)
    ax2.set_xlabel("Year", fontsize=10)
    ax2.set_title("New GLP-1 Trial Registrations by Year (2020–2026)", fontsize=11, pad=8)
    for y, ct in zip(trial_years, trial_counts):
        ax2.text(y, ct + 0.5, str(ct), ha="center", fontsize=9)

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
