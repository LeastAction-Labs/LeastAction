# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
description = "Marketing — campaign performance executive summary (MTD through 2026-05-10)"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Marketing — Campaign Performance</title><style>
*{box-sizing:border-box}
body{margin:0;padding:16px;background:#eef0f2;font:13px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#222}
.wrap{max-width:680px;margin:0 auto;background:#fff;padding:22px 22px 26px;border:1px solid #e3e6e8;border-radius:4px}
.hd{border-bottom:3px solid #4a1a6b;padding-bottom:8px;margin-bottom:6px}
h1{font-size:18px;margin:0;color:#4a1a6b}
.sub{font-size:12px;color:#555;margin:2px 0 0}
.meta{font-size:11px;color:#999;margin:6px 0 16px}
h2{font-size:12px;margin:20px 0 7px;color:#4a1a6b;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #e3e6e8;padding-bottom:4px}
table{border-collapse:collapse;width:100%}
.kpi td{width:25%;padding:9px 6px;border:1px solid #eef0f2;text-align:center;vertical-align:top;background:#fafbfc}
.kpi .v{font-size:17px;font-weight:700;color:#4a1a6b;display:block;line-height:1.2}
.kpi .l{font-size:9.5px;color:#888;text-transform:uppercase;letter-spacing:.3px}
.kpi .d{font-size:10.5px;font-weight:600;display:block;margin-top:2px}
.dt th{background:#4a1a6b;color:#fff;padding:6px 8px;text-align:left;font-size:11px;white-space:nowrap}
.dt td{padding:5px 8px;border-bottom:1px solid #eef0f2;font-size:11px}
.dt td.r,.dt th.r{text-align:right}
.dt tr:nth-child(even) td{background:#faf7fc}
.dt tr.total td{background:#4a1a6b;color:#fff;font-weight:700}
.pos{color:#1a7a3f}.neg{color:#b91c1c}
.cols{width:100%}.cols td{vertical-align:top;width:33.33%;padding:0 5px}
.cols h3{font-size:11px;margin:0 0 5px;color:#4a1a6b}
.foot{font-size:10px;color:#aaa;margin-top:18px;border-top:1px solid #eef0f2;padding-top:8px}
@media(max-width:600px){body{padding:8px}.wrap{padding:14px}.kpi td{padding:6px 3px}.kpi .v{font-size:14px}.dt th,.dt td{padding:4px 5px}.cols td{display:block;width:100%;padding:0 0 12px}}
</style></head><body><div class="wrap">
<div class="hd"><h1>Marketing &mdash; Campaign Performance</h1>
<p class="sub">Paid &amp; owned media &middot; spend, reach and return</p></div>
<p class="meta">Period: 2026-05-01 to 2026-05-10 &nbsp;|&nbsp; Generated: 2026-05-11 06:00 UTC &nbsp;|&nbsp; Source: marketing_analytics &middot; USD</p>

<h2>Highlights &mdash; MTD</h2>
<table class="kpi"><tr>
<td><span class="v">$41,690</span><span class="l">Total Spend</span><span class="d pos">-1.4% vs plan</span></td>
<td><span class="v">$170,901</span><span class="l">Attributed Rev</span><span class="d pos">+12.8% YoY</span></td>
<td><span class="v">4.1x</span><span class="l">Blended ROAS</span><span class="d pos">+0.2x</span></td>
<td><span class="v">4,392</span><span class="l">Conversions</span><span class="d pos">+9.6% YoY</span></td>
</tr><tr>
<td><span class="v">$9.49</span><span class="l">Blended CPA</span><span class="d pos">-4.1%</span></td>
<td><span class="v">2.3%</span><span class="l">Avg CTR</span><span class="d pos">+0.2 pp</span></td>
<td><span class="v">4.2%</span><span class="l">Conv. Rate</span><span class="d pos">+0.3 pp</span></td>
<td><span class="v">4.69M</span><span class="l">Impressions</span><span class="d pos">+6.1%</span></td>
</tr></table>
<p class="meta">Best campaign: Email Newsletter (8.4x ROAS) &nbsp;|&nbsp; Watch: Brand Awareness Q2 (2.8x) &nbsp;|&nbsp; YoY = vs same period FY2025</p>

<h2>Conversion Funnel &mdash; MTD</h2>
<table class="dt">
<tr><th>Stage</th><th class="r">Volume</th><th class="r">Step Rate</th><th class="r">vs LW</th></tr>
<tr><td>Impressions</td><td class="r">4,685,000</td><td class="r">&mdash;</td><td class="r pos">+6.1%</td></tr>
<tr><td>Clicks</td><td class="r">105,640</td><td class="r">2.3%</td><td class="r pos">+0.2 pp</td></tr>
<tr><td>Sessions</td><td class="r">98,420</td><td class="r">93.2%</td><td class="r pos">+1.1 pp</td></tr>
<tr><td>Add-to-cart</td><td class="r">14,210</td><td class="r">14.4%</td><td class="r pos">+0.6 pp</td></tr>
<tr><td>Conversions</td><td class="r">4,392</td><td class="r">30.9%</td><td class="r pos">+0.4 pp</td></tr>
</table>

<h2>Campaign Performance &mdash; MTD</h2>
<table class="dt">
<tr><th>Campaign</th><th>Channel</th><th class="r">Spend ($)</th><th class="r">Clicks</th><th class="r">CTR</th><th class="r">Conv.</th><th class="r">ROAS</th></tr>
<tr><td>Email Newsletter</td><td>Email</td><td class="r">1,180</td><td class="r">6,240</td><td class="r">13.0%</td><td class="r">624</td><td class="r pos">8.4x</td></tr>
<tr><td>Laptop Promo May</td><td>Google Shopping</td><td class="r">9,820</td><td class="r">17,800</td><td class="r">4.0%</td><td class="r">1,068</td><td class="r pos">5.1x</td></tr>
<tr><td>Spring Sale 2026</td><td>Google Search</td><td class="r">14,280</td><td class="r">26,760</td><td class="r">3.0%</td><td class="r">1,338</td><td class="r">4.2x</td></tr>
<tr><td>Retargeting May</td><td>Display</td><td class="r">3,920</td><td class="r">8,840</td><td class="r">1.3%</td><td class="r">442</td><td class="r">3.7x</td></tr>
<tr><td>Influencer Tech</td><td>Instagram</td><td class="r">4,850</td><td class="r">20,800</td><td class="r">4.0%</td><td class="r">416</td><td class="r">3.1x</td></tr>
<tr><td>Brand Awareness Q2</td><td>Facebook</td><td class="r">7,640</td><td class="r">25,200</td><td class="r">1.2%</td><td class="r">504</td><td class="r neg">2.8x</td></tr>
<tr class="total"><td colspan="2">Total</td><td class="r">41,690</td><td class="r">105,640</td><td class="r">2.3%</td><td class="r">4,392</td><td class="r">4.1x</td></tr>
</table>

<h2>Daily Spend &amp; Conversions &mdash; Past 10 Days</h2>
<table class="dt">
<tr><th>Date</th><th class="r">Spend ($)</th><th class="r">Clicks</th><th class="r">Conv.</th><th class="r">CPA ($)</th><th class="r">ROAS</th></tr>
<tr><td>2026-05-01</td><td class="r">3,950</td><td class="r">9,820</td><td class="r">405</td><td class="r">9.75</td><td class="r">4.0x</td></tr>
<tr><td>2026-05-02</td><td class="r">4,310</td><td class="r">11,140</td><td class="r">462</td><td class="r">9.33</td><td class="r">4.2x</td></tr>
<tr><td>2026-05-03</td><td class="r">3,540</td><td class="r">8,460</td><td class="r">352</td><td class="r">10.06</td><td class="r">3.8x</td></tr>
<tr><td>2026-05-04</td><td class="r">3,610</td><td class="r">8,720</td><td class="r">360</td><td class="r">10.03</td><td class="r">3.9x</td></tr>
<tr><td>2026-05-05</td><td class="r">4,720</td><td class="r">12,310</td><td class="r">528</td><td class="r">8.94</td><td class="r">4.4x</td></tr>
<tr><td>2026-05-06</td><td class="r">4,580</td><td class="r">11,890</td><td class="r">505</td><td class="r">9.07</td><td class="r">4.3x</td></tr>
<tr><td>2026-05-07</td><td class="r">4,090</td><td class="r">10,240</td><td class="r">431</td><td class="r">9.49</td><td class="r">4.0x</td></tr>
<tr><td>2026-05-08</td><td class="r">4,260</td><td class="r">10,810</td><td class="r">456</td><td class="r">9.34</td><td class="r">4.1x</td></tr>
<tr><td>2026-05-09</td><td class="r">4,510</td><td class="r">11,650</td><td class="r">493</td><td class="r">9.15</td><td class="r">4.3x</td></tr>
<tr><td>2026-05-10</td><td class="r">4,120</td><td class="r">10,300</td><td class="r">400</td><td class="r">10.30</td><td class="r">4.0x</td></tr>
<tr class="total"><td>Total</td><td class="r">41,690</td><td class="r">105,640</td><td class="r">4,392</td><td class="r">9.49</td><td class="r">4.1x</td></tr>
</table>

<h2>Top Campaigns by Objective &mdash; MTD</h2>
<table class="cols"><tr>
<td><h3>A &middot; Search</h3>
<table class="dt">
<tr><th>Campaign</th><th class="r">ROAS</th></tr>
<tr><td>Laptop Promo</td><td class="r pos">5.1x</td></tr>
<tr><td>Spring Sale</td><td class="r">4.2x</td></tr>
<tr><td>Brand Terms</td><td class="r">6.8x</td></tr>
<tr><td>Tablet PMax</td><td class="r">3.9x</td></tr>
<tr class="total"><td>Blended</td><td class="r">4.6x</td></tr>
</table></td>
<td><h3>B &middot; Social</h3>
<table class="dt">
<tr><th>Campaign</th><th class="r">ROAS</th></tr>
<tr><td>Influencer Tech</td><td class="r">3.1x</td></tr>
<tr><td>Brand Aware. Q2</td><td class="r neg">2.8x</td></tr>
<tr><td>Reels Launch</td><td class="r">3.4x</td></tr>
<tr><td>TikTok Trial</td><td class="r">2.6x</td></tr>
<tr class="total"><td>Blended</td><td class="r">3.0x</td></tr>
</table></td>
<td><h3>C &middot; Owned</h3>
<table class="dt">
<tr><th>Campaign</th><th class="r">ROAS</th></tr>
<tr><td>Email Newsletter</td><td class="r pos">8.4x</td></tr>
<tr><td>Cart Recovery</td><td class="r pos">11.2x</td></tr>
<tr><td>Loyalty Drop</td><td class="r">7.1x</td></tr>
<tr><td>SMS Promo</td><td class="r">6.3x</td></tr>
<tr class="total"><td>Blended</td><td class="r">8.1x</td></tr>
</table></td>
</tr></table>

<h2>Regional Marketing &mdash; MTD vs LY</h2>
<table class="dt">
<tr><th>Region</th><th class="r">Spend ($)</th><th class="r">Attr. Rev ($)</th><th class="r">ROAS</th><th class="r">LY ROAS</th><th class="r">YoY</th></tr>
<tr><td>North America</td><td class="r">20,845</td><td class="r">87,160</td><td class="r">4.2x</td><td class="r">4.0x</td><td class="r pos">+0.2x</td></tr>
<tr><td>Europe</td><td class="r">10,423</td><td class="r">44,818</td><td class="r">4.3x</td><td class="r">4.0x</td><td class="r pos">+0.3x</td></tr>
<tr><td>Asia Pacific</td><td class="r">6,254</td><td class="r">28,142</td><td class="r">4.5x</td><td class="r">4.1x</td><td class="r pos">+0.4x</td></tr>
<tr><td>Rest of World</td><td class="r">4,168</td><td class="r">10,781</td><td class="r">2.6x</td><td class="r">2.5x</td><td class="r pos">+0.1x</td></tr>
<tr class="total"><td>Total</td><td class="r">41,690</td><td class="r">170,901</td><td class="r">4.1x</td><td class="r">3.9x</td><td class="r">+0.2x</td></tr>
</table>

<h2>Regional &times; Objective &mdash; MTD ROAS</h2>
<table class="dt">
<tr><th>Region</th><th class="r">A Search</th><th class="r">B Social</th><th class="r">C Owned</th><th class="r">Blended</th></tr>
<tr><td>North America</td><td class="r">4.7x</td><td class="r">3.0x</td><td class="r">8.2x</td><td class="r">4.2x</td></tr>
<tr><td>Europe</td><td class="r">4.8x</td><td class="r">3.1x</td><td class="r">8.4x</td><td class="r">4.3x</td></tr>
<tr><td>Asia Pacific</td><td class="r">5.0x</td><td class="r">3.3x</td><td class="r">8.6x</td><td class="r">4.5x</td></tr>
<tr><td>Rest of World</td><td class="r">3.1x</td><td class="r">2.2x</td><td class="r">6.0x</td><td class="r">2.6x</td></tr>
<tr class="total"><td>Blended</td><td class="r">4.6x</td><td class="r">3.0x</td><td class="r">8.1x</td><td class="r">4.1x</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Source: marketing_analytics &middot; ROAS = attributed revenue / spend &middot; Figures in USD.</div>
</div></body></html>"""
