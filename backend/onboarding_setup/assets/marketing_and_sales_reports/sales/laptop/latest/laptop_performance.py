# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
description = "Sales — laptop category daily performance (MTD through 2026-05-10)"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sales — Laptop Performance</title><style>
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
.pos{color:#1a7a3f}.neg{color:#b91c1c}
.cols{width:100%}.cols td{vertical-align:top;width:33.33%;padding:0 5px}
.cols h3{font-size:11px;margin:0 0 5px;color:#1a3a5c}
.foot{font-size:10px;color:#aaa;margin-top:18px;border-top:1px solid #eef0f2;padding-top:8px}
@media(max-width:600px){body{padding:8px}.wrap{padding:14px}.kpi td{padding:6px 3px}.kpi .v{font-size:14px}.dt th,.dt td{padding:4px 5px}.cols td{display:block;width:100%;padding:0 0 12px}}
</style></head><body><div class="wrap">
<div class="hd"><h1>Sales &mdash; Laptop Performance</h1>
<p class="sub">Laptop category &middot; daily sales, returns and momentum</p></div>
<p class="meta">Period: 2026-05-01 to 2026-05-10 &nbsp;|&nbsp; Generated: 2026-05-11 06:00 UTC &nbsp;|&nbsp; Source: ecomm_sales &middot; USD</p>

<h2>Highlights &mdash; MTD</h2>
<table class="kpi"><tr>
<td><span class="v">$307,960</span><span class="l">Revenue</span><span class="d pos">+8.1% YoY</span></td>
<td><span class="v">207</span><span class="l">Units Sold</span><span class="d pos">+5.4% YoY</span></td>
<td><span class="v">$1,488</span><span class="l">Avg Price</span><span class="d pos">+2.6%</span></td>
<td><span class="v">21.4%</span><span class="l">Margin</span><span class="d pos">+0.4 pp</span></td>
</tr><tr>
<td><span class="v">40.0%</span><span class="l">of Total Sales</span><span class="d pos">+0.5 pp</span></td>
<td><span class="v">MacBook Air M3</span><span class="l">#1 Model</span><span class="d pos">$72.8K</span></td>
<td><span class="v">3.7%</span><span class="l">Return Rate</span><span class="d pos">-0.5 pp</span></td>
<td><span class="v">Apple</span><span class="l">Top Brand</span><span class="d pos">39%</span></td>
</tr></table>
<p class="meta">YoY = vs same period FY2025</p>

<h2>Daily Performance &mdash; Past 10 Days</h2>
<table class="dt">
<tr><th>Date</th><th class="r">Units</th><th class="r">Revenue ($)</th><th class="r">Avg Price ($)</th><th class="r">Returns</th><th class="r">Net Units</th><th class="r">Return Rate</th></tr>
<tr><td>2026-05-01</td><td class="r">20</td><td class="r">28,400</td><td class="r">1,420</td><td class="r">1</td><td class="r">19</td><td class="r">5.0%</td></tr>
<tr><td>2026-05-02</td><td class="r">22</td><td class="r">30,960</td><td class="r">1,407</td><td class="r">1</td><td class="r">21</td><td class="r">4.5%</td></tr>
<tr><td>2026-05-03</td><td class="r">18</td><td class="r">25,360</td><td class="r">1,409</td><td class="r">2</td><td class="r">16</td><td class="r">11.1%</td></tr>
<tr><td>2026-05-04</td><td class="r">18</td><td class="r">25,720</td><td class="r">1,429</td><td class="r">0</td><td class="r">18</td><td class="r">0.0%</td></tr>
<tr><td>2026-05-05</td><td class="r">24</td><td class="r">34,200</td><td class="r">1,425</td><td class="r">1</td><td class="r">23</td><td class="r">4.2%</td></tr>
<tr><td>2026-05-06</td><td class="r">24</td><td class="r">33,400</td><td class="r">1,392</td><td class="r">0</td><td class="r">24</td><td class="r">0.0%</td></tr>
<tr><td>2026-05-07</td><td class="r">22</td><td class="r">30,400</td><td class="r">1,382</td><td class="r">1</td><td class="r">21</td><td class="r">4.5%</td></tr>
<tr><td>2026-05-08</td><td class="r">23</td><td class="r">32,000</td><td class="r">1,391</td><td class="r">1</td><td class="r">22</td><td class="r">4.3%</td></tr>
<tr><td>2026-05-09</td><td class="r">25</td><td class="r">34,760</td><td class="r">1,390</td><td class="r">1</td><td class="r">24</td><td class="r">4.0%</td></tr>
<tr><td>2026-05-10</td><td class="r">23</td><td class="r">32,760</td><td class="r">1,424</td><td class="r">0</td><td class="r">23</td><td class="r">0.0%</td></tr>
<tr class="total"><td>Total</td><td class="r">219</td><td class="r">307,960</td><td class="r">1,406</td><td class="r">8</td><td class="r">211</td><td class="r">3.7%</td></tr>
</table>

<h2>Brand Breakdown &mdash; MTD</h2>
<table class="dt">
<tr><th>Brand</th><th class="r">Units</th><th class="r">Revenue ($)</th><th class="r">Share</th><th class="r">Margin %</th><th class="r">YoY</th></tr>
<tr><td>Apple</td><td class="r">76</td><td class="r">120,776</td><td class="r">39.2%</td><td class="r">18.6%</td><td class="r pos">+7.2%</td></tr>
<tr><td>Dell</td><td class="r">56</td><td class="r">75,200</td><td class="r">24.4%</td><td class="r">23.1%</td><td class="r pos">+6.4%</td></tr>
<tr><td>Lenovo</td><td class="r">22</td><td class="r">35,200</td><td class="r">11.4%</td><td class="r">23.7%</td><td class="r pos">+9.8%</td></tr>
<tr><td>HP</td><td class="r">20</td><td class="r">30,000</td><td class="r">9.7%</td><td class="r">24.2%</td><td class="r pos">+5.1%</td></tr>
<tr><td>Asus</td><td class="r">18</td><td class="r">18,000</td><td class="r">5.8%</td><td class="r">26.4%</td><td class="r pos">+12.3%</td></tr>
<tr><td>Others</td><td class="r">15</td><td class="r">28,784</td><td class="r">9.3%</td><td class="r">21.0%</td><td class="r pos">+8.0%</td></tr>
<tr class="total"><td>Total</td><td class="r">207</td><td class="r">307,960</td><td class="r">100.0%</td><td class="r">21.4%</td><td class="r">+8.1%</td></tr>
</table>

<h2>Top Models by Tier &mdash; MTD</h2>
<table class="cols"><tr>
<td><h3>A &middot; Premium</h3>
<table class="dt">
<tr><th>Model</th><th class="r">Rev ($)</th></tr>
<tr><td>MacBook Pro 14"</td><td class="r">47,976</td></tr>
<tr><td>Razer Blade 15</td><td class="r">10,120</td></tr>
<tr><td>MSI Creator 15</td><td class="r">7,464</td></tr>
<tr class="total"><td>Tier</td><td class="r">65,560</td></tr>
</table></td>
<td><h3>B &middot; Mainstream</h3>
<table class="dt">
<tr><th>Model</th><th class="r">Rev ($)</th></tr>
<tr><td>MacBook Air M3</td><td class="r">72,800</td></tr>
<tr><td>Dell XPS 15</td><td class="r">60,800</td></tr>
<tr><td>ThinkPad X1</td><td class="r">35,200</td></tr>
<tr><td>HP Spectre x360</td><td class="r">30,000</td></tr>
<tr class="total"><td>Tier</td><td class="r">198,800</td></tr>
</table></td>
<td><h3>C &middot; Value</h3>
<table class="dt">
<tr><th>Model</th><th class="r">Rev ($)</th></tr>
<tr><td>Asus ZenBook 14</td><td class="r">18,000</td></tr>
<tr><td>Dell Inspiron 15</td><td class="r">14,400</td></tr>
<tr><td>Surface Laptop 5</td><td class="r">11,200</td></tr>
<tr class="total"><td>Tier</td><td class="r">43,600</td></tr>
</table></td>
</tr></table>

<h2>Regional Laptop Sales &mdash; MTD vs LY</h2>
<table class="dt">
<tr><th>Region</th><th class="r">Revenue ($)</th><th class="r">Share</th><th class="r">Units</th><th class="r">LY ($)</th><th class="r">YoY %</th></tr>
<tr><td>North America</td><td class="r">153,980</td><td class="r">50.0%</td><td class="r">104</td><td class="r">142,720</td><td class="r pos">+7.9%</td></tr>
<tr><td>Europe</td><td class="r">76,990</td><td class="r">25.0%</td><td class="r">52</td><td class="r">68,865</td><td class="r pos">+11.8%</td></tr>
<tr><td>Asia Pacific</td><td class="r">46,194</td><td class="r">15.0%</td><td class="r">31</td><td class="r">38,690</td><td class="r pos">+19.4%</td></tr>
<tr><td>Rest of World</td><td class="r">30,796</td><td class="r">10.0%</td><td class="r">20</td><td class="r">27,135</td><td class="r pos">+13.5%</td></tr>
<tr class="total"><td>Total</td><td class="r">307,960</td><td class="r">100.0%</td><td class="r">207</td><td class="r">277,410</td><td class="r">+11.0%</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Source: ecomm_sales &middot; LY = last-year same period &middot; Figures in USD.</div>
</div></body></html>"""
