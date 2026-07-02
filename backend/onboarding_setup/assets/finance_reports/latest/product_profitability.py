# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
description = "Finance — product & category profitability (MTD through 2026-05-10)"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Finance — Product Profitability</title><style>
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
.dt tr.total td{background:#1a4731;color:#fff;font-weight:700}
.pos{color:#1a7a3f}.neg{color:#b91c1c}
.cols{width:100%}.cols td{vertical-align:top;width:33.33%;padding:0 5px}
.cols h3{font-size:11px;margin:0 0 5px;color:#1a4731}
.foot{font-size:10px;color:#aaa;margin-top:18px;border-top:1px solid #eef0f2;padding-top:8px}
@media(max-width:600px){body{padding:8px}.wrap{padding:14px}.kpi td{padding:6px 3px}.kpi .v{font-size:14px}.dt th,.dt td{padding:4px 5px}.cols td{display:block;width:100%;padding:0 0 12px}}
</style></head><body><div class="wrap">
<div class="hd"><h1>Finance &mdash; Product Profitability</h1>
<p class="sub">Margin &amp; gross-profit contribution by product and category</p></div>
<p class="meta">Period: 2026-05-01 to 2026-05-10 &nbsp;|&nbsp; Generated: 2026-05-11 06:00 UTC &nbsp;|&nbsp; Source: finance_ledger &middot; USD</p>

<h2>Highlights &mdash; MTD</h2>
<table class="kpi"><tr>
<td><span class="v">$259,225</span><span class="l">Gross Profit</span><span class="d pos">+12.5% YoY</span></td>
<td><span class="v">37.0%</span><span class="l">Blended Margin</span><span class="d pos">+0.6 pp</span></td>
<td><span class="v">Accessories</span><span class="l">Top Margin Cat.</span><span class="d pos">42.8%</span></td>
<td><span class="v">Laptops</span><span class="l">Top GP Driver</span><span class="d pos">$65.9K</span></td>
</tr><tr>
<td><span class="v">$441,384</span><span class="l">Total COGS</span><span class="d neg">63.0% of net</span></td>
<td><span class="v">$60.49</span><span class="l">GP / Order</span><span class="d pos">+1.8%</span></td>
<td><span class="v">Furniture</span><span class="l">Highest Item GM</span><span class="d pos">33.2%</span></td>
<td><span class="v">2</span><span class="l">Margin Alerts</span><span class="d neg">&lt; 19% GM</span></td>
</tr></table>
<p class="meta">Net revenue $700,609 &nbsp;|&nbsp; Gross margin = gross profit / net revenue &nbsp;|&nbsp; YoY = vs same period FY2025</p>

<h2>Category Profitability &mdash; MTD</h2>
<table class="dt">
<tr><th>Category</th><th class="r">Net Rev ($)</th><th class="r">COGS ($)</th><th class="r">Gross Profit ($)</th><th class="r">Margin %</th><th class="r">GP Share</th></tr>
<tr><td>Accessories</td><td class="r">154,134</td><td class="r">88,165</td><td class="r">65,969</td><td class="r">42.8%</td><td class="r">25.4%</td></tr>
<tr><td>Laptops</td><td class="r">280,244</td><td class="r">220,272</td><td class="r">59,972</td><td class="r">21.4%</td><td class="r">23.1%</td></tr>
<tr><td>Electronics</td><td class="r">84,073</td><td class="r">63,791</td><td class="r">20,282</td><td class="r">24.1%</td><td class="r">7.8%</td></tr>
<tr><td>Tablets</td><td class="r">105,091</td><td class="r">82,707</td><td class="r">22,384</td><td class="r">21.3%</td><td class="r">8.6%</td></tr>
<tr><td>Furniture</td><td class="r">49,043</td><td class="r">32,761</td><td class="r">16,282</td><td class="r">33.2%</td><td class="r">6.3%</td></tr>
<tr><td>Other</td><td class="r">28,024</td><td class="r">17,235</td><td class="r">10,789</td><td class="r">38.5%</td><td class="r">4.2%</td></tr>
<tr class="total"><td>Total</td><td class="r">700,609</td><td class="r">441,384</td><td class="r">259,225</td><td class="r">37.0%</td><td class="r">100.0%</td></tr>
</table>

<h2>Top Gross-Profit Contributors by Line &mdash; MTD</h2>
<table class="cols"><tr>
<td><h3>A &middot; Laptops</h3>
<table class="dt">
<tr><th>Product</th><th class="r">GP ($)</th><th class="r">GM%</th></tr>
<tr><td>Dell XPS 15</td><td class="r">13,619</td><td class="r">22.4%</td></tr>
<tr><td>MacBook Air M3</td><td class="r">13,250</td><td class="r">18.2%</td></tr>
<tr><td>MacBook Pro 14"</td><td class="r">9,307</td><td class="r">19.4%</td></tr>
<tr><td>ThinkPad X1</td><td class="r">8,342</td><td class="r">23.7%</td></tr>
<tr><td>HP Spectre</td><td class="r">7,260</td><td class="r">24.2%</td></tr>
<tr class="total"><td>Top 5</td><td class="r">51,778</td><td class="r">21.0%</td></tr>
</table></td>
<td><h3>B &middot; Accessories</h3>
<table class="dt">
<tr><th>Product</th><th class="r">GP ($)</th><th class="r">GM%</th></tr>
<tr><td>Sony WH-1000XM5</td><td class="r">17,878</td><td class="r">38.2%</td></tr>
<tr><td>USB-C Hub</td><td class="r">12,158</td><td class="r">51.3%</td></tr>
<tr><td>LG 27" Monitor</td><td class="r">11,540</td><td class="r">31.4%</td></tr>
<tr><td>Logitech MX 3</td><td class="r">11,068</td><td class="r">42.1%</td></tr>
<tr><td>Anker 65W GaN</td><td class="r">6,461</td><td class="r">45.5%</td></tr>
<tr class="total"><td>Top 5</td><td class="r">59,105</td><td class="r">41.2%</td></tr>
</table></td>
<td><h3>C &middot; Tablets</h3>
<table class="dt">
<tr><th>Product</th><th class="r">GP ($)</th><th class="r">GM%</th></tr>
<tr><td>iPad Pro 12.9"</td><td class="r">9,745</td><td class="r">21.3%</td></tr>
<tr><td>iPad Air</td><td class="r">6,049</td><td class="r">21.3%</td></tr>
<tr><td>Galaxy Tab S9</td><td class="r">4,090</td><td class="r">21.3%</td></tr>
<tr><td>iPad 10th Gen</td><td class="r">2,747</td><td class="r">21.3%</td></tr>
<tr><td>Surface Pro 9</td><td class="r">1,967</td><td class="r">21.3%</td></tr>
<tr class="total"><td>Top 5</td><td class="r">24,598</td><td class="r">21.3%</td></tr>
</table></td>
</tr></table>

<h2>Margin Trend &mdash; Past 10 Days</h2>
<table class="dt">
<tr><th>Date</th><th class="r">Net Rev ($)</th><th class="r">Gross Profit ($)</th><th class="r">Margin %</th><th class="r">DoD pp</th></tr>
<tr><td>2026-05-01</td><td class="r">64,610</td><td class="r">23,907</td><td class="r">37.0%</td><td class="r">&mdash;</td></tr>
<tr><td>2026-05-02</td><td class="r">70,434</td><td class="r">26,061</td><td class="r">37.0%</td><td class="r">0.0</td></tr>
<tr><td>2026-05-03</td><td class="r">57,694</td><td class="r">21,058</td><td class="r">36.5%</td><td class="r neg">-0.5</td></tr>
<tr><td>2026-05-04</td><td class="r">58,513</td><td class="r">21,357</td><td class="r">36.5%</td><td class="r">0.0</td></tr>
<tr><td>2026-05-05</td><td class="r">77,805</td><td class="r">29,177</td><td class="r">37.5%</td><td class="r pos">+1.0</td></tr>
<tr><td>2026-05-06</td><td class="r">75,985</td><td class="r">28,494</td><td class="r">37.5%</td><td class="r">0.0</td></tr>
<tr><td>2026-05-07</td><td class="r">69,160</td><td class="r">25,589</td><td class="r">37.0%</td><td class="r neg">-0.5</td></tr>
<tr><td>2026-05-08</td><td class="r">72,800</td><td class="r">26,936</td><td class="r">37.0%</td><td class="r">0.0</td></tr>
<tr><td>2026-05-09</td><td class="r">79,079</td><td class="r">29,655</td><td class="r">37.5%</td><td class="r pos">+0.5</td></tr>
<tr><td>2026-05-10</td><td class="r">74,529</td><td class="r">27,576</td><td class="r">37.0%</td><td class="r neg">-0.5</td></tr>
<tr class="total"><td>Total</td><td class="r">700,609</td><td class="r">259,225</td><td class="r">37.0%</td><td class="r"></td></tr>
</table>

<h2>Regional Margin &mdash; MTD vs LY</h2>
<table class="dt">
<tr><th>Region</th><th class="r">Gross Profit ($)</th><th class="r">Margin %</th><th class="r">LY Margin %</th><th class="r">YoY pp</th></tr>
<tr><td>Asia Pacific</td><td class="r">40,985</td><td class="r">39.0%</td><td class="r">37.8%</td><td class="r pos">+1.2</td></tr>
<tr><td>Europe</td><td class="r">66,558</td><td class="r">38.0%</td><td class="r">37.5%</td><td class="r pos">+0.5</td></tr>
<tr><td>Middle East</td><td class="r">7,777</td><td class="r">37.0%</td><td class="r">36.6%</td><td class="r pos">+0.4</td></tr>
<tr><td>North America</td><td class="r">126,109</td><td class="r">36.0%</td><td class="r">35.6%</td><td class="r pos">+0.4</td></tr>
<tr><td>Latin America</td><td class="r">14,713</td><td class="r">35.0%</td><td class="r">34.9%</td><td class="r pos">+0.1</td></tr>
<tr><td>Africa</td><td class="r">2,382</td><td class="r">34.0%</td><td class="r">33.2%</td><td class="r pos">+0.8</td></tr>
<tr class="total"><td>Total</td><td class="r">259,225</td><td class="r">37.0%</td><td class="r">36.4%</td><td class="r">+0.6</td></tr>
</table>

<h2>Low-Margin Watchlist</h2>
<table class="dt">
<tr><th>Product</th><th>Category</th><th class="r">Net Rev ($)</th><th class="r">Margin %</th><th class="r">Target %</th><th class="r">Gap pp</th></tr>
<tr><td>MacBook Air M3</td><td>Laptops</td><td class="r">72,800</td><td class="r">18.2%</td><td class="r">20.0%</td><td class="r neg">-1.8</td></tr>
<tr><td>MSI Creator 15</td><td>Laptops</td><td class="r">21,800</td><td class="r">18.6%</td><td class="r">20.0%</td><td class="r neg">-1.4</td></tr>
<tr><td>Razer Blade 15</td><td>Laptops</td><td class="r">27,400</td><td class="r">20.1%</td><td class="r">20.0%</td><td class="r pos">+0.1</td></tr>
</table>
<p class="meta">Action: review supplier pricing &amp; promo depth on flagged SKUs ahead of next buying cycle.</p>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Source: finance_ledger &middot; Margin = gross profit / net revenue &middot; Figures in USD.</div>
</div></body></html>"""
