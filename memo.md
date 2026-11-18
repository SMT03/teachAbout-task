# Memo: TECHi traffic and content - what the data supports

Sources. Two files are used and never mixed. `techi_articles.csv` is real, scraped (120 rows, 20 per section; crawl dates 2026-05-18..2026-11-09). `traffic_table.csv` is the supplied 12-month dataset (2025-09..2026-08); its monthly figures are given inputs, not verified web analytics.

## (a) Is "up 30% YoY" true?
Not demonstrated. A same-month YoY needs a month-12 pair; the file holds 12 months, so available prior-year pairs = 0. The proxies bracket 30% but never equal it:
- Raw endpoints 2025-09 -> 2026-08: 57,500 -> 102,805 = +78.79%.
- Raw half-over-half (mean/month): 63,580 -> 98,185.7 = +54.43%.
- Adjusted endpoints: 57,500 -> 71,374.2 = +24.13%.
- Adjusted half-over-half: 60,730 -> 68,167.1 = +12.25%.

The raw figures are inflated by the 1 Feb 2026 tracking artefact. Jan->Feb total rose +47.95% ((94,685-64,000)/64,000) while the independent signup counter rose only +3.26% ((950-920)/920); ratio 1.4795/1.0326 = 1.4327. All six sections jumped 41-49% in one month (AI +49.10%, Markets +48.25%, Crypto +47.54%, Breakthroughs +48.41%, Policy +47.50%, Guides +41.08%). Six unrelated audiences do not grow in lockstep; shared instrumentation does. Conversion fell 1.3621% -> 1.0607% (-22.13%); at the boundary 1.4375% -> 1.0033% (-30.20%).

## (b) Best estimate of underlying change
+12.25%, the artefact-adjusted half-over-half figure (uses all 12 months). The de-spiked, deflated endpoints (A = 1.4795/1.0271 = 1.4404) give +24.13%. So underlying growth is roughly +12% to +24%. "Up 30%" sits above both adjusted proxies.

## (c) Retire Guides - Yes
Guides is the only section whose sessions fall, and the fall survives every adjustment: pre avg 3,900.0 -> post avg 2,382.1 = -38.92% raw, and -57.59% artefact-adjusted (a uniform A deepens genuine declines). It is also the smallest section. Retire it on traffic grounds, not on output (see below).

## Finding 1 (techi_articles.csv)
Headline formats are near-uniform: of 120 headlines, 113 are standard, 3 question, 3 how-to, 1 list. The site almost never uses listicle, how-to or question framing. Word count: mean 11.37, median 11, range 5-16.

## Finding 2 (techi_articles.csv)
Company naming is section-dependent, not site-wide. Overall 80/120 (66.7%) name a company and 77/120 (64.2%) contain a number. Markets is 20/20 on both, mean 13.3 words; Guides is 8/20 company, 10/20 number, mean 9.9 words. Markets headlines are short, named and number-heavy; Guides are longer and more generic.

## Finding linking the scrape to the traffic table
The note "Guides has published almost nothing since Mar 2026" is contradicted by the real scrape: 20 Guides posts after Mar 2026, 10 in July 2026 alone, median gap 3 days. Yet the traffic table shows Guides sessions collapsing (5,220 in 2026-02 -> 725 in 2026-08). Falling traffic is not falling output; the note conflates them. Data ambiguity: the two files share only section names, with no article-level join key, so any link is section-level association, not attribution. On the AI note, the scrape starts 2026-05-18 and has no Sep-2025 rows, so it cannot confirm a September 2025 hire: not verifiable.

## Recommendation and cost if wrong
Report +12% to +24% underlying, not "up 30%", and retire Guides. Cost if wrong: if the Feb jump was real growth we under-report and under-invest; if Guides' decline was a pure artefact we lose a cheap, steadily published section.

I would change my mind if the analytics vendor confirmed no snippet change on 1 Feb 2026, or an independent counter (e.g. server logs) reproduced the same +47.95% jump.

## The next number I want (free to obtain)
Google Search Console clicks and impressions, month by month, 2025-09..2026-08. It is free, independent of the analytics snippet, and would show whether the Feb jump is a tracking change or real demand.
