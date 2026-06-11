# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
description = "Finance — gross-to-net P&L executive summary (MTD through 2026-05-10)"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Finance — Gross-to-Net Summary</title><style>
*{box-sizing:border-box}
body{margin:0;padding:16px;background:#eef0f2;font:13px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#222}
.wrap{max-width:680px;margin:0 auto;background:#fff;padding:22px 22px 26px;border:1px solid #e3e6e8;border-radius:4px}
.hd{border-bottom:3px solid #1a4731;padding-bottom:8px;margin-bottom:6px}
h1{font-size:18px;margin:0;color:#1a4731}
.sub{font-size:12px;color:#555;margin:2px 0 0}
.meta{font-size:11px;color:#999;margin:6px 0 16px}
h2{font-size:12px;margin:20px 0 7px;color:#1a4731;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #e3e6e8;padding-bottom:4px}
table{border-collapse:collapse;width:100%}
.kpi td{width:25%;padding:9px 6px;border:1px solid #eef0f2;text-align:center;vertical-align:top;background:#fafbfc}
.kpi .v{font-size:17px;font-weight:700;color:#1a4731;display:block;line-height:1.2}
.kpi .l{font-size:9.5px;color:#888;text-transform:uppercase;letter-spacing:.3px}
.kpi .d{font-size:10.5px;font-weight:600;display:block;margin-top:2px}
.dt th{background:#1a4731;color:#fff;padding:6px 8px;text-align:left;font-size:11px;white-space:nowrap}
.dt td{padding:5px 8px;border-bottom:1px solid #eef0f2;font-size:11px}
.dt td.r,.dt th.r{text-align:right}
.dt tr:nth-child(even) td{background:#fafbfc}
.dt tr.sub td{font-weight:600;background:#eef4f0}
.dt tr.total td{background:#1a4731;color:#fff;font-weight:700}
.pos{color:#1a7a3f}.neg{color:#b91c1c}
.cols{width:100%}.cols td{vertical-align:top;width:33.33%;padding:0 5px}
.cols h3{font-size:11px;margin:0 0 5px;color:#1a4731}
.foot{font-size:10px;color:#aaa;margin-top:18px;border-top:1px solid #eef0f2;padding-top:8px}
@media(max-width:600px){body{padding:8px}.wrap{padding:14px}.kpi td{padding:6px 3px}.kpi .v{font-size:14px}.dt th,.dt td{padding:4px 5px}.cols td{display:block;width:100%;padding:0 0 12px}}
</style></head><body><div class="wrap">
<div class="hd"><h1>Finance &mdash; Gross-to-Net Summary</h1>
<p class="sub">Month-to-date P&amp;L &middot; revenue, margin and profitability</p></div>
<p class="meta">Period: 2026-05-01 to 2026-05-10 &nbsp;|&nbsp; Generated: 2026-05-11 06:00 UTC &nbsp;|&nbsp; Source: finance_ledger &middot; USD</p>

<h2>Highlights &mdash; MTD</h2>
<table class="kpi"><tr>
<td><span class="v">$769,900</span><span class="l">Gross Revenue</span><span class="d pos">+10.1% YoY</span></td>
<td><span class="v">$700,609</span><span class="l">Net Revenue</span><span class="d pos">+10.3% YoY</span></td>
<td><span class="v">$259,225</span><span class="l">Gross Profit</span><span class="d pos">+0.6 pp GM</span></td>
<td><span class="v">37.0%</span><span class="l">Gross Margin</span><span class="d pos">+0.6 pp</span></td>
</tr><tr>
<td><span class="v">$91,079</span><span class="l">Operating Income</span><span class="d pos">+8.4% YoY</span></td>
<td><span class="v">13.0%</span><span class="l">Op. Margin</span><span class="d pos">+0.8 pp</span></td>
<td><span class="v">$68,309</span><span class="l">Net Income</span><span class="d pos">9.7% of net</span></td>
<td><span class="v">9.0%</span><span class="l">Discount + Return</span><span class="d pos">-0.4 pp</span></td>
</tr></table>
<p class="meta">Discounts $46,194 (6.0% of gross) &nbsp;|&nbsp; Returns &amp; refunds $23,097 (3.0%) &nbsp;|&nbsp; YoY = vs same period FY2025</p>

<h2>Gross-to-Net Waterfall &mdash; MTD</h2>
<table class="dt">
<tr><th>Line item</th><th class="r">Amount ($)</th><th class="r">% of Gross</th><th class="r">YoY %</th></tr>
<tr><td>Gross revenue</td><td class="r">769,900</td><td class="r">100.0%</td><td class="r pos">+10.1%</td></tr>
<tr><td>&nbsp;&nbsp;Less: discounts &amp; promotions</td><td class="r neg">(46,194)</td><td class="r">-6.0%</td><td class="r">-5.8%</td></tr>
<tr><td>&nbsp;&nbsp;Less: returns &amp; refunds</td><td class="r neg">(23,097)</td><td class="r">-3.0%</td><td class="r">-2.1%</td></tr>
<tr class="sub"><td>Net revenue</td><td class="r">700,609</td><td class="r">91.0%</td><td class="r pos">+10.3%</td></tr>
<tr><td>&nbsp;&nbsp;Less: cost of goods sold</td><td class="r neg">(441,384)</td><td class="r">-57.3%</td><td class="r">+9.4%</td></tr>
<tr class="sub"><td>Gross profit</td><td class="r">259,225</td><td class="r">33.7%</td><td class="r pos">+12.5%</td></tr>
<tr><td>&nbsp;&nbsp;Less: operating expenses</td><td class="r neg">(168,146)</td><td class="r">-21.8%</td><td class="r">+6.9%</td></tr>
<tr class="sub"><td>Operating income (EBIT)</td><td class="r">91,079</td><td class="r">11.8%</td><td class="r pos">+8.4%</td></tr>
<tr><td>&nbsp;&nbsp;Less: interest &amp; tax</td><td class="r neg">(22,770)</td><td class="r">-3.0%</td><td class="r">+4.1%</td></tr>
<tr class="total"><td>Net income</td><td class="r">68,309</td><td class="r">8.9%</td><td class="r">+11.0%</td></tr>
</table>

<h2>Operating Expense Breakdown &mdash; MTD</h2>
<table class="dt">
<tr><th>Category</th><th class="r">Amount ($)</th><th class="r">% of Net Rev</th><th class="r">Budget ($)</th><th class="r">Var %</th></tr>
<tr><td>Fulfillment &amp; logistics</td><td class="r">56,049</td><td class="r">8.0%</td><td class="r">57,000</td><td class="r pos">-1.7%</td></tr>
<tr><td>Payroll &amp; G&amp;A</td><td class="r">52,545</td><td class="r">7.5%</td><td class="r">52,000</td><td class="r neg">+1.0%</td></tr>
<tr><td>Marketing</td><td class="r">41,690</td><td class="r">6.0%</td><td class="r">43,000</td><td class="r pos">-3.0%</td></tr>
<tr><td>Technology &amp; other</td><td class="r">17,862</td><td class="r">2.6%</td><td class="r">18,500</td><td class="r pos">-3.4%</td></tr>
<tr class="total"><td>Total OpEx</td><td class="r">168,146</td><td class="r">24.0%</td><td class="r">170,500</td><td class="r">-1.4%</td></tr>
</table>

<h2>Daily P&amp;L Trend &mdash; Past 10 Days</h2>
<table class="dt">
<tr><th>Date</th><th class="r">Gross ($)</th><th class="r">Net ($)</th><th class="r">Gross Profit ($)</th><th class="r">GM %</th><th class="r">DoD %</th></tr>
<tr><td>2026-05-01</td><td class="r">71,000</td><td class="r">64,610</td><td class="r">23,907</td><td class="r">37.0%</td><td class="r">&mdash;</td></tr>
<tr><td>2026-05-02</td><td class="r">77,400</td><td class="r">70,434</td><td class="r">26,061</td><td class="r">37.0%</td><td class="r pos">+9.0%</td></tr>
<tr><td>2026-05-03</td><td class="r">63,400</td><td class="r">57,694</td><td class="r">21,058</td><td class="r">36.5%</td><td class="r neg">-18.1%</td></tr>
<tr><td>2026-05-04</td><td class="r">64,300</td><td class="r">58,513</td><td class="r">21,357</td><td class="r">36.5%</td><td class="r pos">+1.4%</td></tr>
<tr><td>2026-05-05</td><td class="r">85,500</td><td class="r">77,805</td><td class="r">29,177</td><td class="r">37.5%</td><td class="r pos">+33.0%</td></tr>
<tr><td>2026-05-06</td><td class="r">83,500</td><td class="r">75,985</td><td class="r">28,494</td><td class="r">37.5%</td><td class="r neg">-2.3%</td></tr>
<tr><td>2026-05-07</td><td class="r">76,000</td><td class="r">69,160</td><td class="r">25,589</td><td class="r">37.0%</td><td class="r neg">-9.0%</td></tr>
<tr><td>2026-05-08</td><td class="r">80,000</td><td class="r">72,800</td><td class="r">26,936</td><td class="r">37.0%</td><td class="r pos">+5.3%</td></tr>
<tr><td>2026-05-09</td><td class="r">86,900</td><td class="r">79,079</td><td class="r">29,655</td><td class="r">37.5%</td><td class="r pos">+8.6%</td></tr>
<tr><td>2026-05-10</td><td class="r">81,900</td><td class="r">74,529</td><td class="r">27,576</td><td class="r">37.0%</td><td class="r neg">-5.8%</td></tr>
<tr class="total"><td>Total</td><td class="r">769,900</td><td class="r">700,609</td><td class="r">259,225</td><td class="r">37.0%</td><td class="r"></td></tr>
</table>

<h2>Gross Profit by Line &mdash; MTD</h2>
<table class="cols"><tr>
<td><h3>A &middot; Laptops</h3>
<table class="dt">
<tr><th>Product</th><th class="r">GP ($)</th></tr>
<tr><td>MacBook Air M3</td><td class="r">13,250</td></tr>
<tr><td>Dell XPS 15</td><td class="r">13,619</td></tr>
<tr><td>MacBook Pro 14"</td><td class="r">9,307</td></tr>
<tr><td>ThinkPad X1</td><td class="r">8,342</td></tr>
<tr><td>HP Spectre x360</td><td class="r">7,260</td></tr>
<tr class="total"><td>GM 21.4%</td><td class="r">65,903</td></tr>
</table></td>
<td><h3>B &middot; Accessories</h3>
<table class="dt">
<tr><th>Product</th><th class="r">GP ($)</th></tr>
<tr><td>Sony WH-1000XM5</td><td class="r">17,878</td></tr>
<tr><td>USB-C Hub 7-in-1</td><td class="r">12,158</td></tr>
<tr><td>LG 27" Monitor</td><td class="r">11,540</td></tr>
<tr><td>Logitech MX 3</td><td class="r">11,068</td></tr>
<tr><td>Anker 65W GaN</td><td class="r">6,461</td></tr>
<tr class="total"><td>GM 42.8%</td><td class="r">72,494</td></tr>
</table></td>
<td><h3>C &middot; Tablets</h3>
<table class="dt">
<tr><th>Product</th><th class="r">GP ($)</th></tr>
<tr><td>iPad Pro 12.9"</td><td class="r">9,745</td></tr>
<tr><td>iPad Air</td><td class="r">6,049</td></tr>
<tr><td>Galaxy Tab S9</td><td class="r">4,090</td></tr>
<tr><td>iPad 10th Gen</td><td class="r">2,747</td></tr>
<tr><td>Surface Pro 9</td><td class="r">1,967</td></tr>
<tr class="total"><td>GM 21.3%</td><td class="r">24,598</td></tr>
</table></td>
</tr></table>

<h2>Regional P&amp;L &mdash; MTD vs LY</h2>
<table class="dt">
<tr><th>Region</th><th class="r">Net Rev ($)</th><th class="r">Gross Profit ($)</th><th class="r">GM %</th><th class="r">LY Net ($)</th><th class="r">YoY %</th></tr>
<tr><td>North America</td><td class="r">350,304</td><td class="r">126,109</td><td class="r">36.0%</td><td class="r">323,159</td><td class="r pos">+8.4%</td></tr>
<tr><td>Europe</td><td class="r">175,152</td><td class="r">66,558</td><td class="r">38.0%</td><td class="r">157,511</td><td class="r pos">+11.2%</td></tr>
<tr><td>Asia Pacific</td><td class="r">105,091</td><td class="r">40,985</td><td class="r">39.0%</td><td class="r">88,534</td><td class="r pos">+18.7%</td></tr>
<tr><td>Latin America</td><td class="r">42,037</td><td class="r">14,713</td><td class="r">35.0%</td><td class="r">40,001</td><td class="r pos">+5.1%</td></tr>
<tr><td>Middle East</td><td class="r">21,018</td><td class="r">7,777</td><td class="r">37.0%</td><td class="r">18,388</td><td class="r pos">+14.3%</td></tr>
<tr><td>Africa</td><td class="r">7,007</td><td class="r">2,382</td><td class="r">34.0%</td><td class="r">5,739</td><td class="r pos">+22.1%</td></tr>
<tr class="total"><td>Total</td><td class="r">700,609</td><td class="r">259,225</td><td class="r">37.0%</td><td class="r">635,332</td><td class="r">+10.3%</td></tr>
</table>

<h2>Regional &times; Top Line &mdash; MTD Gross Profit ($)</h2>
<table class="dt">
<tr><th>Region</th><th class="r">A Laptops</th><th class="r">B Accessories</th><th class="r">C Tablets</th><th class="r">YoY</th></tr>
<tr><td>North America</td><td class="r">32,952</td><td class="r">36,247</td><td class="r">12,299</td><td class="r pos">+8.0%</td></tr>
<tr><td>Europe</td><td class="r">16,476</td><td class="r">18,124</td><td class="r">6,150</td><td class="r pos">+11.5%</td></tr>
<tr><td>Asia Pacific</td><td class="r">9,885</td><td class="r">10,874</td><td class="r">3,690</td><td class="r pos">+19.1%</td></tr>
<tr><td>Rest of World</td><td class="r">6,590</td><td class="r">7,249</td><td class="r">2,459</td><td class="r pos">+13.6%</td></tr>
<tr class="total"><td>Total</td><td class="r">65,903</td><td class="r">72,494</td><td class="r">24,598</td><td class="r">+12.5%</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Source: finance_ledger &middot; Net revenue = gross less discounts &amp; returns &middot; Figures in USD.</div>
</div></body></html>"""
