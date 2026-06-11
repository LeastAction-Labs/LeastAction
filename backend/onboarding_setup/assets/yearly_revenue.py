# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
skill_name = "ReportExplorer/report_explorer_assistant"
description = "Annual executive summary — cross-domain (finance, sales, marketing) for FY2025"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Annual Executive Summary</title><style>
*{box-sizing:border-box}
body{margin:0;padding:16px;background:#eef0f2;font:13px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#222}
.wrap{max-width:680px;margin:0 auto;background:#fff;padding:22px 22px 26px;border:1px solid #e3e6e8;border-radius:4px}
.hd{border-bottom:3px solid #1f3a5f;padding-bottom:8px;margin-bottom:6px}
h1{font-size:18px;margin:0;color:#1f3a5f}
.sub{font-size:12px;color:#555;margin:2px 0 0}
.meta{font-size:11px;color:#999;margin:6px 0 16px}
h2{font-size:12px;margin:20px 0 7px;color:#1f3a5f;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #e3e6e8;padding-bottom:4px}
table{border-collapse:collapse;width:100%}
.kpi td{width:25%;padding:9px 6px;border:1px solid #eef0f2;text-align:center;vertical-align:top;background:#fafbfc}
.kpi .v{font-size:17px;font-weight:700;color:#1f3a5f;display:block;line-height:1.2}
.kpi .l{font-size:9.5px;color:#888;text-transform:uppercase;letter-spacing:.3px}
.kpi .d{font-size:10.5px;font-weight:600;display:block;margin-top:2px}
.dt th{background:#1f3a5f;color:#fff;padding:6px 8px;text-align:left;font-size:11px;white-space:nowrap}
.dt td{padding:5px 8px;border-bottom:1px solid #eef0f2;font-size:11px}
.dt td.r,.dt th.r{text-align:right}
.dt tr:nth-child(even) td{background:#fafbfc}
.dt tr.total td{background:#1f3a5f;color:#fff;font-weight:700}
.pos{color:#1a7a3f}.neg{color:#b91c1c}
.cols{width:100%}.cols td{vertical-align:top;width:33.33%;padding:0 5px}
.cols h3{font-size:11px;margin:0 0 5px;color:#1f3a5f}
.foot{font-size:10px;color:#aaa;margin-top:18px;border-top:1px solid #eef0f2;padding-top:8px}
@media(max-width:600px){body{padding:8px}.wrap{padding:14px}.kpi td{padding:6px 3px}.kpi .v{font-size:14px}.dt th,.dt td{padding:4px 5px}.cols td{display:block;width:100%;padding:0 0 12px}}
</style></head><body><div class="wrap">
<div class="hd"><h1>Annual Executive Summary</h1>
<p class="sub">Company-wide performance &mdash; Sales &middot; Finance &middot; Marketing</p></div>
<p class="meta">Fiscal year: FY2025 (Jan&ndash;Dec 2025) &nbsp;|&nbsp; Generated: 2026-01-15 06:00 UTC &nbsp;|&nbsp; Currency: USD</p>

<h2>Highlights &mdash; FY2025</h2>
<table class="kpi"><tr>
<td><span class="v">$25.64M</span><span class="l">Gross Revenue</span><span class="d pos">+11.8% YoY</span></td>
<td><span class="v">$23.33M</span><span class="l">Net Revenue</span><span class="d pos">+11.5% YoY</span></td>
<td><span class="v">158,200</span><span class="l">Orders</span><span class="d pos">+9.2% YoY</span></td>
<td><span class="v">$162.10</span><span class="l">Avg Order Value</span><span class="d pos">+2.4% YoY</span></td>
</tr><tr>
<td><span class="v">36.8%</span><span class="l">Gross Margin</span><span class="d pos">+0.7 pp</span></td>
<td><span class="v">12.6%</span><span class="l">Op. Margin</span><span class="d pos">+1.1 pp</span></td>
<td><span class="v">$2.23M</span><span class="l">Net Income</span><span class="d pos">+18.4% YoY</span></td>
<td><span class="v">4.1x</span><span class="l">Marketing ROAS</span><span class="d pos">+0.3x</span></td>
</tr></table>
<p class="meta">2026 YTD (through 05-10) gross $8.61M &nbsp;|&nbsp; YTD YoY +12.7% &nbsp;|&nbsp; Active customers 412K (+14.6% YoY) &nbsp;|&nbsp; YoY = vs FY2024</p>

<h2>Performance by Domain</h2>
<table class="dt">
<tr><th>Domain</th><th class="r">FY2025</th><th class="r">YoY</th><th class="r">Headline Metric</th></tr>
<tr><td>Sales (ecomm)</td><td class="r">$25,640,000</td><td class="r pos">+11.8%</td><td class="r">158,200 orders</td></tr>
<tr><td>Finance (P&amp;L)</td><td class="r">$23,332,400 net</td><td class="r pos">+1.1 pp OM</td><td class="r">Net income $2.23M</td></tr>
<tr><td>Marketing</td><td class="r">$1,438,000 spend</td><td class="r pos">4.1x ROAS</td><td class="r">$5.90M attributed</td></tr>
</table>

<h2>Product Category Breakdown</h2>
<table class="dt">
<tr><th>Category</th><th class="r">Revenue ($)</th><th class="r">Share</th><th class="r">Units</th><th class="r">Margin %</th><th class="r">YoY</th></tr>
<tr><td>Laptops</td><td class="r">10,256,000</td><td class="r">40.0%</td><td class="r">7,326</td><td class="r">21.5%</td><td class="r pos">+9.4%</td></tr>
<tr><td>Accessories</td><td class="r">5,640,800</td><td class="r">22.0%</td><td class="r">140,150</td><td class="r">42.6%</td><td class="r pos">+16.2%</td></tr>
<tr><td>Tablets</td><td class="r">3,846,000</td><td class="r">15.0%</td><td class="r">27,040</td><td class="r">21.2%</td><td class="r pos">+7.1%</td></tr>
<tr><td>Electronics</td><td class="r">3,076,800</td><td class="r">12.0%</td><td class="r">10,590</td><td class="r">24.0%</td><td class="r pos">+10.5%</td></tr>
<tr><td>Furniture</td><td class="r">1,794,800</td><td class="r">7.0%</td><td class="r">4,730</td><td class="r">33.1%</td><td class="r pos">+6.0%</td></tr>
<tr><td>Other</td><td class="r">1,025,600</td><td class="r">4.0%</td><td class="r">17,980</td><td class="r">38.4%</td><td class="r pos">+12.3%</td></tr>
<tr class="total"><td>Total</td><td class="r">25,640,000</td><td class="r">100.0%</td><td class="r">207,816</td><td class="r">27.3%</td><td class="r">+11.8%</td></tr>
</table>

<h2>Revenue Trend &mdash; Past 5 Years</h2>
<table class="dt">
<tr><th>Year</th><th class="r">Gross ($)</th><th class="r">Net ($)</th><th class="r">Orders</th><th class="r">YoY %</th><th class="r">Net Margin</th></tr>
<tr><td>FY2021</td><td class="r">12,480,000</td><td class="r">11,356,800</td><td class="r">82,100</td><td class="r">&mdash;</td><td class="r">7.4%</td></tr>
<tr><td>FY2022</td><td class="r">16,210,000</td><td class="r">14,751,100</td><td class="r">104,600</td><td class="r pos">+29.9%</td><td class="r">7.9%</td></tr>
<tr><td>FY2023</td><td class="r">19,540,000</td><td class="r">17,781,400</td><td class="r">124,300</td><td class="r pos">+20.5%</td><td class="r">8.3%</td></tr>
<tr><td>FY2024</td><td class="r">22,930,000</td><td class="r">20,866,300</td><td class="r">144,800</td><td class="r pos">+17.3%</td><td class="r">8.2%</td></tr>
<tr><td>FY2025</td><td class="r">25,640,000</td><td class="r">23,332,400</td><td class="r">158,200</td><td class="r pos">+11.8%</td><td class="r">8.7%</td></tr>
<tr class="total"><td>5-yr CAGR</td><td class="r">19.7%</td><td class="r">&mdash;</td><td class="r">17.8%</td><td class="r"></td><td class="r"></td></tr>
</table>

<h2>Top Products by Line &mdash; FY2025</h2>
<table class="cols"><tr>
<td><h3>A &middot; Laptops</h3>
<table class="dt">
<tr><th>Product</th><th class="r">Rev ($M)</th></tr>
<tr><td>MacBook Air M3</td><td class="r">2.42</td></tr>
<tr><td>Dell XPS 15</td><td class="r">2.02</td></tr>
<tr><td>MacBook Pro 14"</td><td class="r">1.60</td></tr>
<tr><td>ThinkPad X1</td><td class="r">1.17</td></tr>
<tr><td>HP Spectre x360</td><td class="r">1.00</td></tr>
<tr class="total"><td>Top 5</td><td class="r">8.21</td></tr>
</table></td>
<td><h3>B &middot; Accessories</h3>
<table class="dt">
<tr><th>Product</th><th class="r">Rev ($M)</th></tr>
<tr><td>Sony WH-1000XM5</td><td class="r">1.56</td></tr>
<tr><td>LG 27" Monitor</td><td class="r">1.22</td></tr>
<tr><td>Logitech MX 3</td><td class="r">0.88</td></tr>
<tr><td>USB-C Hub 7-in-1</td><td class="r">0.79</td></tr>
<tr><td>Anker 65W GaN</td><td class="r">0.47</td></tr>
<tr class="total"><td>Top 5</td><td class="r">4.92</td></tr>
</table></td>
<td><h3>C &middot; Tablets</h3>
<table class="dt">
<tr><th>Product</th><th class="r">Rev ($M)</th></tr>
<tr><td>iPad Pro 12.9"</td><td class="r">1.52</td></tr>
<tr><td>iPad Air</td><td class="r">0.95</td></tr>
<tr><td>Galaxy Tab S9</td><td class="r">0.64</td></tr>
<tr><td>iPad 10th Gen</td><td class="r">0.43</td></tr>
<tr><td>Surface Pro 9</td><td class="r">0.31</td></tr>
<tr class="total"><td>Top 5</td><td class="r">3.85</td></tr>
</table></td>
</tr></table>

<h2>Regional Performance &mdash; Year &amp; YoY</h2>
<table class="dt">
<tr><th>Region</th><th class="r">FY2025 ($)</th><th class="r">Share</th><th class="r">FY2024 ($)</th><th class="r">YoY %</th></tr>
<tr><td>North America</td><td class="r">12,820,000</td><td class="r">50.0%</td><td class="r">11,826,000</td><td class="r pos">+8.4%</td></tr>
<tr><td>Europe</td><td class="r">6,410,000</td><td class="r">25.0%</td><td class="r">5,764,000</td><td class="r pos">+11.2%</td></tr>
<tr><td>Asia Pacific</td><td class="r">3,846,000</td><td class="r">15.0%</td><td class="r">3,240,000</td><td class="r pos">+18.7%</td></tr>
<tr><td>Latin America</td><td class="r">1,538,400</td><td class="r">6.0%</td><td class="r">1,463,700</td><td class="r pos">+5.1%</td></tr>
<tr><td>Middle East</td><td class="r">769,200</td><td class="r">3.0%</td><td class="r">673,000</td><td class="r pos">+14.3%</td></tr>
<tr><td>Africa</td><td class="r">256,400</td><td class="r">1.0%</td><td class="r">210,000</td><td class="r pos">+22.1%</td></tr>
<tr class="total"><td>Total</td><td class="r">25,640,000</td><td class="r">100.0%</td><td class="r">22,930,000</td><td class="r">+11.8%</td></tr>
</table>

<h2>Regional &times; Top Line &mdash; FY2025 Revenue ($M)</h2>
<table class="dt">
<tr><th>Region</th><th class="r">A Laptops</th><th class="r">B Accessories</th><th class="r">C Tablets</th><th class="r">YoY</th></tr>
<tr><td>North America</td><td class="r">5.13</td><td class="r">2.82</td><td class="r">1.92</td><td class="r pos">+8.9%</td></tr>
<tr><td>Europe</td><td class="r">2.56</td><td class="r">1.41</td><td class="r">0.96</td><td class="r pos">+11.9%</td></tr>
<tr><td>Asia Pacific</td><td class="r">1.54</td><td class="r">0.85</td><td class="r">0.58</td><td class="r pos">+19.2%</td></tr>
<tr><td>Rest of World</td><td class="r">1.03</td><td class="r">0.56</td><td class="r">0.39</td><td class="r pos">+14.1%</td></tr>
<tr class="total"><td>Total</td><td class="r">10.26</td><td class="r">5.64</td><td class="r">3.85</td><td class="r">+11.8%</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Auto-generated executive summary &middot; Sources: ecomm_sales, finance_ledger, marketing_analytics &middot; Figures in USD.</div>
</div></body></html>"""
