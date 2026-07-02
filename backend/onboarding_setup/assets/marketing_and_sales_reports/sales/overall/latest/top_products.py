# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
description = "Sales — top products & category performance (MTD through 2026-05-10)"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sales — Top Products</title><style>
*{box-sizing:border-box}
body{margin:0;padding:16px;background:#eef0f2;font:13px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#222}
.wrap{max-width:680px;margin:0 auto;background:#fff;padding:22px 22px 26px;border:1px solid #e3e6e8;border-radius:4px}
.hd{border-bottom:3px solid #1a3a5c;padding-bottom:8px;margin-bottom:6px}
h1{font-size:18px;margin:0;color:#1a3a5c}
.sub{font-size:12px;color:#555;margin:2px 0 0}
.meta{font-size:11px;color:#999;margin:6px 0 16px}
h2{font-size:12px;margin:20px 0 7px;color:#1a3a5c;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #e3e6e8;padding-bottom:4px}
table{border-collapse:collapse;width:100%}
.kpi td{width:25%;padding:9px 6px;border:1px solid #eef0f2;text-align:center;vertical-align:top;background:#fafbfc}
.kpi .v{font-size:17px;font-weight:700;color:#1a3a5c;display:block;line-height:1.2}
.kpi .l{font-size:9.5px;color:#888;text-transform:uppercase;letter-spacing:.3px}
.kpi .d{font-size:10.5px;font-weight:600;display:block;margin-top:2px}
.dt th{background:#1a3a5c;color:#fff;padding:6px 8px;text-align:left;font-size:11px;white-space:nowrap}
.dt td{padding:5px 8px;border-bottom:1px solid #eef0f2;font-size:11px}
.dt td.r,.dt th.r{text-align:right}
.dt tr:nth-child(even) td{background:#f3f6f9}
.dt tr.total td{background:#1a3a5c;color:#fff;font-weight:700}
.rank{color:#999;font-size:10px}
.pos{color:#1a7a3f}.neg{color:#b91c1c}
.cols{width:100%}.cols td{vertical-align:top;width:33.33%;padding:0 5px}
.cols h3{font-size:11px;margin:0 0 5px;color:#1a3a5c}
.foot{font-size:10px;color:#aaa;margin-top:18px;border-top:1px solid #eef0f2;padding-top:8px}
@media(max-width:600px){body{padding:8px}.wrap{padding:14px}.kpi td{padding:6px 3px}.kpi .v{font-size:14px}.dt th,.dt td{padding:4px 5px}.cols td{display:block;width:100%;padding:0 0 12px}}
</style></head><body><div class="wrap">
<div class="hd"><h1>Sales &mdash; Top Products</h1>
<p class="sub">Best sellers, category mix and product momentum</p></div>
<p class="meta">Period: 2026-05-01 to 2026-05-10 &nbsp;|&nbsp; Generated: 2026-05-11 06:00 UTC &nbsp;|&nbsp; Source: ecomm_sales &middot; USD</p>

<h2>Highlights &mdash; MTD</h2>
<table class="kpi"><tr>
<td><span class="v">$769,900</span><span class="l">Revenue</span><span class="d pos">+10.1% YoY</span></td>
<td><span class="v">6,242</span><span class="l">Units Sold</span><span class="d pos">+7.3% YoY</span></td>
<td><span class="v">MacBook Air M3</span><span class="l">#1 Product</span><span class="d pos">$72.8K</span></td>
<td><span class="v">Laptops</span><span class="l">Top Category</span><span class="d pos">40.0%</span></td>
</tr><tr>
<td><span class="v">27.4%</span><span class="l">Avg Margin</span><span class="d pos">+0.6 pp</span></td>
<td><span class="v">$162.57</span><span class="l">Avg Order Value</span><span class="d pos">+1.4%</span></td>
<td><span class="v">USB-C Hub</span><span class="l">Most Units</span><span class="d pos">632</span></td>
<td><span class="v">3.2%</span><span class="l">Return Rate</span><span class="d pos">-0.4 pp</span></td>
</tr></table>
<p class="meta">YoY = vs same period FY2025</p>

<h2>Category Breakdown &mdash; MTD</h2>
<table class="dt">
<tr><th>Category</th><th class="r">Revenue ($)</th><th class="r">Share</th><th class="r">Units</th><th class="r">Margin %</th><th class="r">YoY</th></tr>
<tr><td>Laptops</td><td class="r">307,960</td><td class="r">40.0%</td><td class="r">220</td><td class="r">21.4%</td><td class="r pos">+8.1%</td></tr>
<tr><td>Accessories</td><td class="r">169,378</td><td class="r">22.0%</td><td class="r">2,117</td><td class="r">42.8%</td><td class="r pos">+14.6%</td></tr>
<tr><td>Tablets</td><td class="r">115,485</td><td class="r">15.0%</td><td class="r">241</td><td class="r">21.3%</td><td class="r pos">+6.2%</td></tr>
<tr><td>Electronics</td><td class="r">92,388</td><td class="r">12.0%</td><td class="r">103</td><td class="r">24.1%</td><td class="r pos">+9.4%</td></tr>
<tr><td>Furniture</td><td class="r">53,893</td><td class="r">7.0%</td><td class="r">77</td><td class="r">33.2%</td><td class="r pos">+4.8%</td></tr>
<tr><td>Other</td><td class="r">30,796</td><td class="r">4.0%</td><td class="r">684</td><td class="r">38.5%</td><td class="r pos">+11.0%</td></tr>
<tr class="total"><td>Total</td><td class="r">769,900</td><td class="r">100.0%</td><td class="r">3,442</td><td class="r">27.4%</td><td class="r">+10.1%</td></tr>
</table>

<h2>Top 10 Products &mdash; MTD</h2>
<table class="dt">
<tr><th>#</th><th>Product</th><th>Category</th><th class="r">Units</th><th class="r">Revenue ($)</th><th class="r">Margin %</th></tr>
<tr><td class="rank">1</td><td>MacBook Air M3</td><td>Laptops</td><td class="r">52</td><td class="r">72,800</td><td class="r">18.2%</td></tr>
<tr><td class="rank">2</td><td>Dell XPS 15</td><td>Laptops</td><td class="r">38</td><td class="r">60,800</td><td class="r">22.4%</td></tr>
<tr><td class="rank">3</td><td>MacBook Pro 14"</td><td>Laptops</td><td class="r">24</td><td class="r">47,976</td><td class="r">19.4%</td></tr>
<tr><td class="rank">4</td><td>Sony WH-1000XM5</td><td>Accessories</td><td class="r">156</td><td class="r">46,800</td><td class="r">38.2%</td></tr>
<tr><td class="rank">5</td><td>iPad Pro 12.9"</td><td>Tablets</td><td class="r">92</td><td class="r">45,750</td><td class="r">21.3%</td></tr>
<tr><td class="rank">6</td><td>LG 27" Monitor</td><td>Accessories</td><td class="r">123</td><td class="r">36,750</td><td class="r">31.4%</td></tr>
<tr><td class="rank">7</td><td>ThinkPad X1</td><td>Laptops</td><td class="r">22</td><td class="r">35,200</td><td class="r">23.7%</td></tr>
<tr><td class="rank">8</td><td>HP Spectre x360</td><td>Laptops</td><td class="r">20</td><td class="r">30,000</td><td class="r">24.2%</td></tr>
<tr><td class="rank">9</td><td>iPad Air</td><td>Tablets</td><td class="r">47</td><td class="r">28,400</td><td class="r">21.3%</td></tr>
<tr><td class="rank">10</td><td>Logitech MX 3</td><td>Accessories</td><td class="r">239</td><td class="r">26,290</td><td class="r">42.1%</td></tr>
<tr class="total"><td colspan="3">Top 10</td><td class="r">813</td><td class="r">430,766</td><td class="r">24.6%</td></tr>
</table>

<h2>Top Sellers by Line &mdash; MTD</h2>
<table class="cols"><tr>
<td><h3>A &middot; Laptops</h3>
<table class="dt">
<tr><th>Product</th><th class="r">Rev ($)</th></tr>
<tr><td>MacBook Air M3</td><td class="r">72,800</td></tr>
<tr><td>Dell XPS 15</td><td class="r">60,800</td></tr>
<tr><td>MacBook Pro 14"</td><td class="r">47,976</td></tr>
<tr><td>ThinkPad X1</td><td class="r">35,200</td></tr>
<tr><td>HP Spectre x360</td><td class="r">30,000</td></tr>
<tr class="total"><td>Top 5</td><td class="r">246,776</td></tr>
</table></td>
<td><h3>B &middot; Accessories</h3>
<table class="dt">
<tr><th>Product</th><th class="r">Rev ($)</th></tr>
<tr><td>Sony WH-1000XM5</td><td class="r">46,800</td></tr>
<tr><td>LG 27" Monitor</td><td class="r">36,750</td></tr>
<tr><td>Logitech MX 3</td><td class="r">26,290</td></tr>
<tr><td>USB-C Hub 7-in-1</td><td class="r">23,700</td></tr>
<tr><td>Anker 65W GaN</td><td class="r">14,200</td></tr>
<tr class="total"><td>Top 5</td><td class="r">147,740</td></tr>
</table></td>
<td><h3>C &middot; Tablets</h3>
<table class="dt">
<tr><th>Product</th><th class="r">Rev ($)</th></tr>
<tr><td>iPad Pro 12.9"</td><td class="r">45,750</td></tr>
<tr><td>iPad Air</td><td class="r">28,400</td></tr>
<tr><td>Galaxy Tab S9</td><td class="r">19,200</td></tr>
<tr><td>iPad 10th Gen</td><td class="r">12,900</td></tr>
<tr><td>Surface Pro 9</td><td class="r">9,235</td></tr>
<tr class="total"><td>Top 5</td><td class="r">115,485</td></tr>
</table></td>
</tr></table>

<h2>Category Trend &mdash; Past 10 Days ($)</h2>
<table class="dt">
<tr><th>Date</th><th class="r">Laptops</th><th class="r">Access.</th><th class="r">Tablets</th><th class="r">Other</th><th class="r">Total</th></tr>
<tr><td>2026-05-01</td><td class="r">28,400</td><td class="r">15,620</td><td class="r">10,650</td><td class="r">16,330</td><td class="r">71,000</td></tr>
<tr><td>2026-05-02</td><td class="r">30,960</td><td class="r">17,028</td><td class="r">11,610</td><td class="r">17,802</td><td class="r">77,400</td></tr>
<tr><td>2026-05-03</td><td class="r">25,360</td><td class="r">13,948</td><td class="r">9,510</td><td class="r">14,582</td><td class="r">63,400</td></tr>
<tr><td>2026-05-04</td><td class="r">25,720</td><td class="r">14,146</td><td class="r">9,645</td><td class="r">14,789</td><td class="r">64,300</td></tr>
<tr><td>2026-05-05</td><td class="r">34,200</td><td class="r">18,810</td><td class="r">12,825</td><td class="r">19,665</td><td class="r">85,500</td></tr>
<tr><td>2026-05-06</td><td class="r">33,400</td><td class="r">18,370</td><td class="r">12,525</td><td class="r">19,205</td><td class="r">83,500</td></tr>
<tr><td>2026-05-07</td><td class="r">30,400</td><td class="r">16,720</td><td class="r">11,400</td><td class="r">17,480</td><td class="r">76,000</td></tr>
<tr><td>2026-05-08</td><td class="r">32,000</td><td class="r">17,600</td><td class="r">12,000</td><td class="r">18,400</td><td class="r">80,000</td></tr>
<tr><td>2026-05-09</td><td class="r">34,760</td><td class="r">19,118</td><td class="r">13,035</td><td class="r">19,987</td><td class="r">86,900</td></tr>
<tr><td>2026-05-10</td><td class="r">32,760</td><td class="r">18,018</td><td class="r">12,285</td><td class="r">18,837</td><td class="r">81,900</td></tr>
<tr class="total"><td>Total</td><td class="r">307,960</td><td class="r">169,378</td><td class="r">115,485</td><td class="r">177,077</td><td class="r">769,900</td></tr>
</table>

<h2>Regional &times; Top Line &mdash; MTD Revenue ($)</h2>
<table class="dt">
<tr><th>Region</th><th class="r">A Laptops</th><th class="r">B Accessories</th><th class="r">C Tablets</th><th class="r">YoY</th></tr>
<tr><td>North America</td><td class="r">153,980</td><td class="r">84,689</td><td class="r">57,743</td><td class="r pos">+7.9%</td></tr>
<tr><td>Europe</td><td class="r">76,990</td><td class="r">42,345</td><td class="r">28,871</td><td class="r pos">+11.8%</td></tr>
<tr><td>Asia Pacific</td><td class="r">46,194</td><td class="r">25,407</td><td class="r">17,323</td><td class="r pos">+19.4%</td></tr>
<tr><td>Rest of World</td><td class="r">30,796</td><td class="r">16,937</td><td class="r">11,548</td><td class="r pos">+13.5%</td></tr>
<tr class="total"><td>Total</td><td class="r">307,960</td><td class="r">169,378</td><td class="r">115,485</td><td class="r">+10.1%</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Source: ecomm_sales &middot; Figures in USD.</div>
</div></body></html>"""
