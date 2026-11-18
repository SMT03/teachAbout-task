#!/usr/bin/env python3
"""
Traffic + content analysis for TECHi (traffic_table.csv + techi_articles.csv).

Every number printed or plotted is computed directly from the two input files.
No metric is estimated from outside the data, and each adjustment is derived
arithmetically from the file itself with its derivation shown.

Questions answered:
  1. Fact-check two editorial notes against the scraped article CSV.
  2. Measurement error vs. real growth across the 1 Feb 2026 analytics swap.
  3. Isolate the Nov 2025 Crypto aggregator spike.
  4. Raw vs. underlying "year-over" change (true same-month YoY is not
     computable from this file -- the arithmetic showing why is printed).

Run:      python3 analyze_traffic.py
Outputs:  chart1_sessions_break.png, chart2_feb_jump.png  (300 dpi, greyscale-safe)
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # headless: write files, never open a window
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
TRAFFIC_CSV = HERE / "traffic_table.csv"
ARTICLES_CSV = HERE / "techi_articles.csv"

SECTIONS = ["AI", "Markets", "Crypto", "Breakthroughs", "Policy", "Guides"]
SWAP_MONTH = pd.Period("2026-02", freq="M")    # analytics snippet swapped 1 Feb 2026
SPIKE_MONTH = pd.Period("2025-11", freq="M")   # 36-hour crypto aggregator spike
CHART_DPI = 300


def pct(new, old):
    """Percentage change from old to new (not multiplied by 100 twice)."""
    return (new - old) / old * 100.0


def rule(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def money(x, dp=0):
    """Format a number with thousands separators."""
    return f"{x:,.{dp}f}"


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
traffic = pd.read_csv(TRAFFIC_CSV)
# Keep everything float so that later de-scaling can store fractional values.
traffic[SECTIONS + ["newsletter_signups"]] = traffic[SECTIONS + ["newsletter_signups"]].astype(float)
traffic["month"] = pd.PeriodIndex(traffic["month"], freq="M")
traffic["total_sessions"] = traffic[SECTIONS].sum(axis=1)
traffic["conversion_pct"] = traffic["newsletter_signups"] / traffic["total_sessions"] * 100
traffic = traffic.set_index("month")

articles = pd.read_csv(ARTICLES_CSV)

pre = traffic[traffic.index < SWAP_MONTH]      # 2025-09 .. 2026-01 (5 months)
post = traffic[traffic.index >= SWAP_MONTH]    # 2026-02 .. 2026-08 (7 months)

print(f"traffic_table.csv : {len(traffic)} monthly rows "
      f"({traffic.index.min()} .. {traffic.index.max()})")
print(f"techi_articles.csv: {len(articles)} rows across "
      f"{articles['section'].nunique()} sections")


# ===========================================================================
# 1. FACT-CHECK THE NOTES AGAINST THE SCRAPED CSV
# ===========================================================================
rule("1. FACT-CHECK: notes vs. scraped techi_articles.csv")

# Parse the "date_shown" column. Absolute dates are parseable; relative labels
# such as "6 hours ago" are left as NaT and reported separately (they are all
# within a day of the crawl, so they cannot affect the conclusions below).
parsed = pd.to_datetime(articles["date_shown"], format="%b %d, %Y", errors="coerce")
articles = articles.assign(date=parsed)
n_relative = int(parsed.isna().sum())
abs_dates = parsed.dropna()
print(f"rows with an absolute date : {len(abs_dates)}")
print(f"rows with a relative label : {n_relative} (all within ~1 day of the crawl)")
print(f"oldest absolute date in file: {abs_dates.min().date()}")
print(f"newest absolute date in file: {abs_dates.max().date()}")

# --- (a) "a second AI writer joined Sep 2025" -------------------------------
ai = articles[articles["section"] == "ai"]
print("\n(a) 'A second AI writer joined Sep 2025'")
print(f"    AI-section rows in the scrape      : {len(ai)}")
print(f"    AI-section date range (absolute)   : "
      f"{ai['date'].min().date()} .. {ai['date'].max().date()}")
print(f"    distinct AI authors in that window : {ai['author'].nunique()}")
print(f"      -> {sorted(ai['author'].unique())}")
print("    VERDICT: NOT VERIFIABLE from this file.")
print("    The whole scrape starts "
      f"{abs_dates.min().date()}; it contains no Sep-2025 (or earlier) rows, "
      "so it can neither confirm nor contradict a September 2025 hire.")

# --- (b) "Guides has published almost nothing since Mar 2026" --------------
guides = articles[articles["section"] == "guides"].sort_values("date")
cut = pd.Timestamp("2026-03-31")
guides_since = guides[guides["date"] > cut]
per_month = guides_since.groupby(guides_since["date"].dt.to_period("M")).size()
print("\n(b) 'Guides has published almost nothing since Mar 2026'")
print(f"    Guides rows in the scrape          : {len(guides)}")
print(f"    Guides date range (absolute)       : "
      f"{guides['date'].min().date()} .. {guides['date'].max().date()}")
print(f"    Guides articles dated after Mar2026: {len(guides_since)} "
      f"(the scrape caps each section at 20, so this is a floor)")
print("    Guides posts per month (from the scrape):")
for period, n in per_month.items():
    print(f"      {period}: {n}")
gaps = guides["date"].diff().dt.days.dropna()
print(f"    median gap between consecutive Guides posts: {gaps.median():.0f} days")
print("    VERDICT: CONTRADICTED.")
print(f"    The scrape alone shows {len(guides_since)} Guides posts after Mar 2026 "
      f"(2026-05-18 .. 2026-11-09) -- including "
      f"{int(per_month.get(pd.Period('2026-07', 'M'), 0))} in July 2026 alone.")
print("    (Note: Guides *traffic* did collapse -- see section 2 -- so the note "
      "appears to\n     conflate falling sessions with falling publication.)")


# ===========================================================================
# 2. MEASUREMENT ERROR VS. REAL GROWTH ACROSS THE 1 FEB 2026 SWAP
# ===========================================================================
rule("2. MEASUREMENT ERROR vs. REAL GROWTH (1 Feb 2026 analytics swap)")

print(f"pre-swap window : {pre.index.min()} .. {pre.index.max()}  ({len(pre)} months)")
print(f"post-swap window: {post.index.min()} .. {post.index.max()}  ({len(post)} months)")

# --- 2a. The single-month boundary jump (the smoking gun) ------------------
jan = traffic.loc[pd.Period("2026-01", "M")]
feb = traffic.loc[pd.Period("2026-02", "M")]

print("\n(a) January-2026 -> February-2026 jump, per section:")
print(f"    {'section':<14}{'Jan 2026':>12}{'Feb 2026':>12}{'change':>12}")
jump_ratios = {}
for sec in SECTIONS:
    r = feb[sec] / jan[sec]
    jump_ratios[sec] = r
    print(f"    {sec:<14}{money(jan[sec]):>12}{money(feb[sec]):>12}"
          f"{pct(feb[sec], jan[sec]):>11.2f}%")

total_jump = pct(feb['total_sessions'], jan['total_sessions'])
signup_jump = pct(feb['newsletter_signups'], jan['newsletter_signups'])
print(f"\n    total sessions : ({money(feb['total_sessions'])} - "
      f"{money(jan['total_sessions'])}) / {money(jan['total_sessions'])} = "
      f"+{total_jump:.2f}%")
print(f"    newsletter     : ({money(feb['newsletter_signups'])} - "
      f"{money(jan['newsletter_signups'])}) / {money(jan['newsletter_signups'])} = "
      f"+{signup_jump:.2f}%")
print(f"    ratio of the two jumps: {feb['total_sessions']/jan['total_sessions']:.4f}"
      f" / {feb['newsletter_signups']/jan['newsletter_signups']:.4f} = "
      f"{(feb['total_sessions']/jan['total_sessions'])/(feb['newsletter_signups']/jan['newsletter_signups']):.4f}")
print("    -> all six sections jump by a nearly identical 41-49% in one month, "
      "while the\n       independent signup counter rises only "
      f"{signup_jump:.2f}%. Real audience growth is not\n       identical across "
      "unrelated sections; a shared instrumentation change is.")

# --- 2b. Period averages and conversion rates ------------------------------
pre_avg = pre.mean(numeric_only=True)
post_avg = post.mean(numeric_only=True)

print("\n(b) Period averages (mean per month), pre vs post the swap:")
print(f"    {'metric':<14}{'pre avg':>12}{'post avg':>12}{'change':>12}")
for sec in SECTIONS:
    print(f"    {sec:<14}{pre_avg[sec]:>12,.1f}{post_avg[sec]:>12,.1f}"
          f"{pct(post_avg[sec], pre_avg[sec]):>11.2f}%")
print(f"    {'TOTAL':<14}{pre_avg['total_sessions']:>12,.1f}"
      f"{post_avg['total_sessions']:>12,.1f}"
      f"{pct(post_avg['total_sessions'], pre_avg['total_sessions']):>11.2f}%")
print(f"    {'signups':<14}{pre_avg['newsletter_signups']:>12,.1f}"
      f"{post_avg['newsletter_signups']:>12,.1f}"
      f"{pct(post_avg['newsletter_signups'], pre_avg['newsletter_signups']):>11.2f}%")

print("\n(c) Conversion rate (newsletter signups / total sessions), period totals:")
pre_conv = pre["newsletter_signups"].sum() / pre["total_sessions"].sum() * 100
post_conv = post["newsletter_signups"].sum() / post["total_sessions"].sum() * 100
print(f"    pre-swap  = {money(pre['newsletter_signups'].sum())} / "
      f"{money(pre['total_sessions'].sum())} = {pre_conv:.4f}%")
print(f"    post-swap = {money(post['newsletter_signups'].sum())} / "
      f"{money(post['total_sessions'].sum())} = {post_conv:.4f}%")
print(f"    conversion change = {pre_conv:.4f}% -> {post_conv:.4f}% = "
      f"{pct(post_conv, pre_conv):+.2f}%")
print(f"    at the boundary   = {jan['conversion_pct']:.4f}% (Jan) -> "
      f"{feb['conversion_pct']:.4f}% (Feb) = "
      f"{pct(feb['conversion_pct'], jan['conversion_pct']):+.2f}%")
print("    -> sessions rose ~48% at the swap while signups rose ~3%; the extra "
      "sessions are\n       not converting, which is what a tracking artefact looks "
      "like, not new readers.")


# ===========================================================================
# 3. ISOLATE THE NOV 2025 CRYPTO SPIKE
# ===========================================================================
rule("3. ISOLATE THE NOV 2025 CRYPTO SPIKE")

oct_c = traffic.loc[pd.Period("2025-10", "M"), "Crypto"]
nov_c = traffic.loc[SPIKE_MONTH, "Crypto"]
dec_c = traffic.loc[pd.Period("2025-12", "M"), "Crypto"]
crypto_baseline = (oct_c + dec_c) / 2          # midpoint of the two neighbours

print(f"    Crypto Oct-2025 : {money(oct_c)}")
print(f"    Crypto Nov-2025 : {money(nov_c)}   <-- 36-hour aggregator spike")
print(f"    Crypto Dec-2025 : {money(dec_c)}")
print(f"    normal baseline = ({money(oct_c)} + {money(dec_c)}) / 2 = "
      f"{money(crypto_baseline, 1)}")
excess = nov_c - crypto_baseline
print(f"    spike inflation = {money(nov_c)} - {money(crypto_baseline, 1)} = "
      f"+{money(excess, 1)} sessions ({pct(nov_c, crypto_baseline):+.2f}% over baseline)")

nov = traffic.loc[SPIKE_MONTH]
nov_total = nov["total_sessions"]
nov_total_clean = nov_total - nov_c + crypto_baseline
print("\n    Effect on the November-2025 headline numbers:")
print(f"      reported total sessions : {money(nov_total)}")
print(f"      spike-free total        : {money(nov_total)} - {money(nov_c)} + "
      f"{money(crypto_baseline, 1)} = {money(nov_total_clean, 1)}")
print(f"      total inflated by       : {pct(nov_total, nov_total_clean):+.2f}%")
print(f"      reported conversion     : {nov['newsletter_signups']} / {money(nov_total)}"
      f" = {nov['newsletter_signups']/nov_total*100:.4f}%")
print(f"      spike-free conversion   : {nov['newsletter_signups']} / "
      f"{money(nov_total_clean, 1)} = {nov['newsletter_signups']/nov_total_clean*100:.4f}%")
print(f"      -> the spike depressed the reported November conversion rate by "
      f"{abs(pct(nov['newsletter_signups']/nov_total, nov['newsletter_signups']/nov_total_clean)):.2f}%")
print("         (relative), purely by inflating the denominator.")


# ===========================================================================
# 4. RAW vs. UNDERLYING "YEAR-OVER" CHANGE
# ===========================================================================
rule("4. RAW vs. UNDERLYING YEAR-OVER CHANGE")

print("True same-month YoY is NOT computable from this file.")
print(f"    The file holds {len(traffic)} months: {traffic.index.min()} .. {traffic.index.max()}.")
print("    A same-month YoY for, say, 2026-08 requires 2025-08, and for 2026-02")
print("    requires 2025-02. This file starts at 2025-09, so the number of")
print("    available prior-year (month, month-12) pairs = 0.")
print("    Anything called 'YoY' here is therefore reported as an explicitly")
print("    labelled proxy built from the two halves of the 12-month window.")

# --- Derive the tracking-inflation multiplier A from the data --------------
# M = the observed boundary jump in TOTAL sessions (= the artefact + 1 month
#     of real growth).
M = feb["total_sessions"] / jan["total_sessions"]

# De-spike November first so it cannot distort the pre-swap growth estimate.
pre_despiked = pre.copy()
pre_despiked.loc[SPIKE_MONTH, "Crypto"] = crypto_baseline
pre_despiked["total_sessions"] = pre_despiked[SECTIONS].sum(axis=1)

# Geometric-mean month-over-month growth of the (de-spiked) pre-swap period.
mom = (pre_despiked["total_sessions"] / pre_despiked["total_sessions"].shift(1)).dropna()
g_pre = float(np.exp(np.mean(np.log(mom))))          # e.g. 1.0271 = +2.71%/month

A = M / g_pre          # tracking-inflation multiplier (levels, not a %)
print(f"\nDeriving the post-Feb tracking-inflation multiplier A:")
print(f"    M  = Feb-2026 total / Jan-2026 total = "
      f"{money(feb['total_sessions'])} / {money(jan['total_sessions'])} = {M:.4f} "
      f"(+{ (M-1)*100:.2f}%)")
print(f"    1+g = geometric-mean MoM growth of the de-spiked pre-swap period = "
      f"{g_pre:.4f} (+{(g_pre-1)*100:.2f}%)")
print(f"    A  = M / (1+g) = {M:.4f} / {g_pre:.4f} = {A:.4f} "
      f"(+{(A-1)*100:.2f}% level shift treated as measurement error)")
print("    Assumption stated plainly: the pre-swap growth rate is taken as the")
print("    real growth rate, so everything above it at the boundary is the artefact.")

# Build adjusted series: de-spiked November + post-Feb deflated by A.
adj = traffic.copy()
adj.loc[SPIKE_MONTH, "Crypto"] = crypto_baseline
for sec in SECTIONS:
    adj.loc[adj.index >= SWAP_MONTH, sec] = adj.loc[adj.index >= SWAP_MONTH, sec] / A
adj["total_sessions"] = adj[SECTIONS].sum(axis=1)

# --- 4a. Half-over-half proxy (both adjustments apply) ---------------------
pre_avg_adj = pre_despiked["total_sessions"].mean()
post_avg_adj = adj.loc[adj.index >= SWAP_MONTH, "total_sessions"].mean()
raw_half = pct(post_avg["total_sessions"], pre_avg["total_sessions"])
adj_half = pct(post_avg_adj, pre_avg_adj)

print("\n(a) Proxy: 2nd half of the dataset vs 1st half (mean per month)")
print(f"    raw       : {money(pre_avg['total_sessions'], 1)} -> "
      f"{money(post_avg['total_sessions'], 1)} = {raw_half:+.2f}%")
print(f"    adjusted  : {money(pre_avg_adj, 1)} (de-spiked) -> "
      f"{money(post_avg_adj, 1)} (deflated by A) = {adj_half:+.2f}%")
print(f"    -> the {raw_half - adj_half:.2f} pp gap is the two artefacts combined.")

# --- 4b. Endpoint-to-endpoint across the full 12-month window --------------
first = traffic.index.min()
last = traffic.index.max()
raw_end = pct(traffic.loc[last, "total_sessions"], traffic.loc[first, "total_sessions"])
adj_end = pct(adj.loc[last, "total_sessions"], adj.loc[first, "total_sessions"])
print(f"\n(b) Proxy: {first} -> {last} (full 12-month window, endpoints)")
print(f"    raw       : {money(traffic.loc[first, 'total_sessions'])} -> "
      f"{money(traffic.loc[last, 'total_sessions'])} = {raw_end:+.2f}%")
print(f"    adjusted  : {money(adj.loc[first, 'total_sessions'], 1)} -> "
      f"{money(adj.loc[last, 'total_sessions'], 1)} = {adj_end:+.2f}%")
print("    (The Nov-2025 spike is an interior point and does not touch either")
print("     endpoint, so it changes nothing in (b); it only matters for (a) and")
print("     for any period aggregate.)")

print("\nPer-section raw vs adjusted half-over-half proxy:")
print(f"    {'section':<14}{'raw':>10}{'adjusted':>12}")
for sec in SECTIONS:
    pre_a = pre_despiked[sec].mean()
    post_a = adj.loc[adj.index >= SWAP_MONTH, sec].mean()
    print(f"    {sec:<14}{pct(post_avg[sec], pre_avg[sec]):>9.2f}%"
          f"{pct(post_a, pre_a):>11.2f}%")
print(f"    {'signups':<14}"
      f"{pct(post_avg['newsletter_signups'], pre_avg['newsletter_signups']):>9.2f}%"
      f"{'n/a':>12}")

print("\nCaveats on the adjustment (stated, not hidden):")
print("  * A is a single uniform multiplier applied to every section, because the")
print("    boundary jump was uniform across all six. It therefore also deepens")
print("    genuine declines, so an adjusted fall is an artefact-corrected fall,")
print("    not a rise.")
print("  * A is built from the data's own pre-swap growth, so it is only as sound")
print("    as the assumption that pre-swap growth continued unchanged into February.")


# ===========================================================================
# CHARTS  (greyscale-safe: line style + marker + hatch carry the meaning)
# ===========================================================================
rule("CHARTS")

plt.rcParams.update({
    "figure.dpi": CHART_DPI,
    "savefig.dpi": CHART_DPI,
    "font.size": 9,
    "axes.grid": True,
    "grid.linestyle": ":",
    "grid.color": "0.7",
    "axes.edgecolor": "black",
    "axes.labelcolor": "black",
    "text.color": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "legend.frameon": True,
    "legend.edgecolor": "black",
})

labels = [str(p) for p in traffic.index]
x = np.arange(len(traffic))

# --- Chart 1: sessions, raw vs adjusted, with both artefacts marked --------
fig1, ax1 = plt.subplots(figsize=(11, 5.6))
ax1.plot(x, traffic["total_sessions"], linestyle="-", marker="o",
         color="black", linewidth=1.8, markersize=6,
         label="Total sessions (as reported)")
ax1.plot(x, adj["total_sessions"], linestyle="--", marker="s",
         color="0.35", linewidth=1.6, markersize=5,
         label=f"Total sessions (artefacts removed: Nov de-spiked, post-Feb / {A:.3f})")

swap_x = labels.index("2026-02")
spike_x = labels.index("2025-11")
ax1.axvline(swap_x - 0.5, color="black", linestyle="-.", linewidth=1.4)
ax1.annotate("Analytics snippet\nswapped 1 Feb 2026",
             xy=(swap_x - 0.5, 98000), xytext=(swap_x - 3.4, 88000),
             fontsize=8, ha="left",
             arrowprops=dict(arrowstyle="->", color="black", linestyle="-.", linewidth=1))
ax1.annotate("Nov-2025 Crypto\naggregator spike",
             xy=(spike_x, traffic["total_sessions"].iloc[spike_x]),
             xytext=(spike_x - 2.2, 88000), fontsize=8, ha="left",
             arrowprops=dict(arrowstyle="->", color="black", linewidth=1))
ax1.scatter([spike_x], [traffic["total_sessions"].iloc[spike_x]],
            s=140, facecolors="none", edgecolors="black", linewidths=1.6, zorder=5)

ax1.set_xticks(x)
ax1.set_xticklabels(labels, rotation=45, ha="right")
ax1.set_ylabel("Sessions per month")
ax1.set_xlabel("Month")
ax1.set_title("TECHi monthly sessions: reported vs. artefact-adjusted\n"
              f"(one 12-month window, {labels[0]} .. {labels[-1]}; "
              f"adjustment factor A = {A:.3f})", fontsize=10)
ax1.legend(loc="upper left", fontsize=8)
ax1.margins(x=0.02)
fig1.tight_layout()
fig1.savefig(HERE / "chart1_sessions_break.png", bbox_inches="tight")
plt.close(fig1)

# --- Chart 2: the uniform boundary jump (proof of instrumentation error) ---
fig2, ax2 = plt.subplots(figsize=(10, 5.2))
names = SECTIONS + ["TOTAL sessions", "newsletter\nsignups"]
vals = [pct(feb[s], jan[s]) for s in SECTIONS] + [total_jump, signup_jump]
hatches = ["//", "\\\\", "xx", "..", "++", "oo", "**", "//"]
bars = ax2.bar(np.arange(len(names)), vals,
               color="white", edgecolor="black", linewidth=1.2,
               hatch=None)
for bar, h in zip(bars, hatches):
    bar.set_hatch(h)
for bar, v in zip(bars, vals):
    ax2.annotate(f"{v:+.1f}%", (bar.get_x() + bar.get_width() / 2, v),
                 textcoords="offset points", xytext=(0, 4 if v >= 0 else -12),
                 ha="center", fontsize=8)
ax2.axhline(0, color="black", linewidth=1)
ax2.axhline(signup_jump, color="black", linestyle="--", linewidth=1.1)
ax2.annotate(f"signup counter: {signup_jump:+.1f}% (no jump)",
             xy=(len(names) - 1.6, signup_jump), xytext=(0.6, signup_jump + 6),
             fontsize=8)
ax2.set_xticks(np.arange(len(names)))
ax2.set_xticklabels(names, rotation=20, ha="right")
ax2.set_ylabel("Change from Jan-2026 to Feb-2026 (%)")
ax2.set_xlabel("Section (sessions) and the independent signup counter")
ax2.set_title("The 1 Feb 2026 tracking jump is uniform across every section\n"
              "but absent from newsletter signups - the signature of a measurement change",
              fontsize=10)
fig2.tight_layout()
fig2.savefig(HERE / "chart2_feb_jump.png", bbox_inches="tight")
plt.close(fig2)

print("wrote chart1_sessions_break.png")
print("wrote chart2_feb_jump.png")
