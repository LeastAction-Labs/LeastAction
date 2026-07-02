# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
description = "Finance — daily P&L snapshot archived 2026-05-05"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Finance — Daily P&L (Archive)</title><style>
*{box-sizing:border-box}
body{margin:0;padding:16px;background:#eef0f2;font:13px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#222}
.wrap{max-width:680px;margin:0 auto;background:#fff;padding:22px 22px 26px;border:1px solid #e3e6e8;border-radius:4px}
.hd{border-bottom:3px solid #1a4731;padding-bottom:8px;margin-bottom:6px}
h1{font-size:18px;margin:0;color:#1a4731}
.sub{font-size:12px;color:#555;margin:2px 0 0}
.meta{font-size:11px;color:#999;margin:6px 0 10px}
.arch{font-size:10.5px;background:#fef3c7;border-left:3px solid #d97706;padding:6px 9px;margin:0 0 14px;color:#92400e}
h2{font-size:12px;margin:20px 0 7px;color:#1a4731;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #e3e6e8;padding-bottom:4px}
table{border-collapse:collapse;width:100%}
.kpi td{width:25%;padding:9px 6px;border:1px solid #eef0f2;text-align:center;vertical-align:top;background:#fafbfc}
.kpi .v{font-size:17px;font-weight:700;color:#1a4731;display:block;line-height:1.2}
.kpi .l{font-size:9.5px;color:#888;text-transform:uppercase;letter-spacing:.3px}
.dt th{background:#1a4731;color:#fff;padding:6px 8px;text-align:left;font-size:11px;white-space:nowrap}
.dt td{padding:5px 8px;border-bottom:1px solid #eef0f2;font-size:11px}
.dt td.r,.dt th.r{text-align:right}
.dt tr:nth-child(even) td{background:#fafbfc}
.dt tr.sub td{font-weight:600;background:#eef4f0}
.dt tr.total td{background:#1a4731;color:#fff;font-weight:700}
.pos{color:#1a7a3f}.neg{color:#b91c1c}
.foot{font-size:10px;color:#aaa;margin-top:18px;border-top:1px solid #eef0f2;padding-top:8px}
@media(max-width:600px){body{padding:8px}.wrap{padding:14px}.kpi td{padding:6px 3px}.kpi .v{font-size:14px}.dt th,.dt td{padding:4px 5px}}
</style></head><body><div class="wrap">
<div class="hd"><h1>Finance &mdash; Daily P&amp;L (Archive)</h1>
<p class="sub">Frozen gross-to-net snapshot</p></div>
<p class="meta">Period: 2026-04-26 to 2026-05-05 &nbsp;|&nbsp; Source: finance_ledger &middot; USD</p>
<div class="arch">&#128190; Archived snapshot &mdash; data frozen at 2026-05-05 23:59 UTC</div>

<h2>Highlights &mdash; 10-Day Window</h2>
<table class="kpi"><tr>
<td><span class="v">$715,600</span><span class="l">Gross Revenue</span></td>
<td><span class="v">$651,196</span><span class="l">Net Revenue</span></td>
<td><span class="v">$240,943</span><span class="l">Gross Profit</span></td>
<td><span class="v">36.9%</span><span class="l">Gross Margin</span></td>
</tr></table>

<h2>Gross-to-Net Waterfall</h2>
<table class="dt">
<tr><th>Line item</th><th class="r">Amount ($)</th><th class="r">% of Gross</th></tr>
<tr><td>Gross revenue</td><td class="r">715,600</td><td class="r">100.0%</td></tr>
<tr><td>&nbsp;&nbsp;Less: discounts &amp; promotions</td><td class="r neg">(42,936)</td><td class="r">-6.0%</td></tr>
<tr><td>&nbsp;&nbsp;Less: returns &amp; refunds</td><td class="r neg">(21,468)</td><td class="r">-3.0%</td></tr>
<tr class="sub"><td>Net revenue</td><td class="r">651,196</td><td class="r">91.0%</td></tr>
<tr><td>&nbsp;&nbsp;Less: cost of goods sold</td><td class="r neg">(410,253)</td><td class="r">-57.3%</td></tr>
<tr class="sub"><td>Gross profit</td><td class="r">240,943</td><td class="r">33.7%</td></tr>
<tr><td>&nbsp;&nbsp;Less: operating expenses</td><td class="r neg">(156,287)</td><td class="r">-21.8%</td></tr>
<tr class="total"><td>Operating income</td><td class="r">84,656</td><td class="r">11.8%</td></tr>
</table>

<h2>Daily P&amp;L Trend</h2>
<table class="dt">
<tr><th>Date</th><th class="r">Gross ($)</th><th class="r">Net ($)</th><th class="r">Gross Profit ($)</th><th class="r">GM %</th></tr>
<tr><td>2026-04-26</td><td class="r">65,000</td><td class="r">59,150</td><td class="r">21,594</td><td class="r">36.5%</td></tr>
<tr><td>2026-04-27</td><td class="r">68,500</td><td class="r">62,335</td><td class="r">22,752</td><td class="r">36.5%</td></tr>
<tr><td>2026-04-28</td><td class="r">73,000</td><td class="r">66,430</td><td class="r">24,579</td><td class="r">37.0%</td></tr>
<tr><td>2026-04-29</td><td class="r">78,000</td><td class="r">70,980</td><td class="r">26,263</td><td class="r">37.0%</td></tr>
<tr><td>2026-04-30</td><td class="r">69,500</td><td class="r">63,245</td><td class="r">23,096</td><td class="r">36.5%</td></tr>
<tr><td>2026-05-01</td><td class="r">71,000</td><td class="r">64,610</td><td class="r">23,907</td><td class="r">37.0%</td></tr>
<tr><td>2026-05-02</td><td class="r">77,400</td><td class="r">70,434</td><td class="r">26,061</td><td class="r">37.0%</td></tr>
<tr><td>2026-05-03</td><td class="r">63,400</td><td class="r">57,694</td><td class="r">21,058</td><td class="r">36.5%</td></tr>
<tr><td>2026-05-04</td><td class="r">64,300</td><td class="r">58,513</td><td class="r">21,357</td><td class="r">36.5%</td></tr>
<tr><td>2026-05-05</td><td class="r">85,500</td><td class="r">77,805</td><td class="r">29,177</td><td class="r">37.5%</td></tr>
<tr class="total"><td>Total</td><td class="r">715,600</td><td class="r">651,196</td><td class="r">240,943</td><td class="r">37.0%</td></tr>
</table>

<h2>Regional P&amp;L</h2>
<table class="dt">
<tr><th>Region</th><th class="r">Net Rev ($)</th><th class="r">Gross Profit ($)</th><th class="r">GM %</th><th class="r">Share</th></tr>
<tr><td>North America</td><td class="r">325,598</td><td class="r">117,215</td><td class="r">36.0%</td><td class="r">50.0%</td></tr>
<tr><td>Europe</td><td class="r">162,799</td><td class="r">61,864</td><td class="r">38.0%</td><td class="r">25.0%</td></tr>
<tr><td>Asia Pacific</td><td class="r">97,679</td><td class="r">38,095</td><td class="r">39.0%</td><td class="r">15.0%</td></tr>
<tr><td>Latin America</td><td class="r">39,072</td><td class="r">13,675</td><td class="r">35.0%</td><td class="r">6.0%</td></tr>
<tr><td>Middle East</td><td class="r">19,536</td><td class="r">7,228</td><td class="r">37.0%</td><td class="r">3.0%</td></tr>
<tr><td>Africa</td><td class="r">6,512</td><td class="r">2,214</td><td class="r">34.0%</td><td class="r">1.0%</td></tr>
<tr class="total"><td>Total</td><td class="r">651,196</td><td class="r">240,291</td><td class="r">36.9%</td><td class="r">100.0%</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Archived finance snapshot &middot; Source: finance_ledger &middot; Figures in USD.</div>
</div></body></html>"""
