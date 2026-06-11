# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
skill_name = "ReportExplorer/report_explorer_assistant"
description = "Daily executive summary — cross-domain (finance, sales, marketing) for 2026-05-10"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Executive Summary</title><style>
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
<div class="hd"><h1>Daily Executive Summary</h1>
<p class="sub">Company-wide performance &mdash; Sales &middot; Finance &middot; Marketing</p></div>
<p class="meta">Reporting day: 2026-05-10 &nbsp;|&nbsp; Generated: 2026-05-11 06:00 UTC &nbsp;|&nbsp; Currency: USD</p>

<h2>Highlights &mdash; 2026-05-10</h2>
<table class="kpi"><tr>
<td><span class="v">$81,900</span><span class="l">Gross Revenue</span><span class="d pos">+29.2% vs LW</span></td>
<td><span class="v">$74,529</span><span class="l">Net Revenue</span><span class="d pos">+28.6% vs LW</span></td>
<td><span class="v">505</span><span class="l">Orders</span><span class="d pos">+8.4% vs LW</span></td>
<td><span class="v">$162.18</span><span class="l">Avg Order Value</span><span class="d neg">-0.3% vs LW</span></td>
</tr><tr>
<td><span class="v">37.0%</span><span class="l">Gross Margin</span><span class="d pos">+0.6 pp</span></td>
<td><span class="v">4.1x</span><span class="l">Marketing ROAS</span><span class="d pos">+0.2x</span></td>
<td><span class="v">3.2%</span><span class="l">Return Rate</span><span class="d pos">-0.4 pp</span></td>
<td><span class="v">68%</span><span class="l">Repeat Buyers</span><span class="d pos">+2 pp</span></td>
</tr></table>
<p class="meta">MTD gross revenue $769,900 &nbsp;|&nbsp; MTD net $700,609 &nbsp;|&nbsp; MTD YoY +10.1% &nbsp;|&nbsp; LW = last week same day (2026-05-03)</p>

<h2>Performance by Domain</h2>
<table class="dt">
<tr><th>Domain</th><th class="r">Today</th><th class="r">MTD</th><th class="r">vs LW / MoM</th><th class="r">Headline Metric</th></tr>
<tr><td>Sales (ecomm)</td><td class="r">$81,900</td><td class="r">$769,900</td><td class="r pos">+29.2%</td><td class="r">AOV $162.18</td></tr>
<tr><td>Finance (P&amp;L)</td><td class="r">$74,529 net</td><td class="r">$700,609 net</td><td class="r pos">+0.6 pp GM</td><td class="r">Op. margin 13.0%</td></tr>
<tr><td>Marketing</td><td class="r">$4,169 spend</td><td class="r">$41,690 spend</td><td class="r pos">4.1x ROAS</td><td class="r">CPA $9.49</td></tr>
</table>

<h2>Product Category Breakdown &mdash; MTD</h2>
<table class="dt">
<tr><th>Category</th><th class="r">Revenue ($)</th><th class="r">Share</th><th class="r">Units</th><th class="r">Margin %</th><th class="r">YoY</th></tr>
<tr><td>Laptops</td><td class="r">307,960</td><td class="r">40.0%</td><td class="r">220</td><td class="r">21.4%</td><td class="r pos">+8.1%</td></tr>
<tr><td>Accessories</td><td class="r">169,378</td><td class="r">22.0%</td><td class="r">4,210</td><td class="r">42.8%</td><td class="r pos">+14.6%</td></tr>
<tr><td>Tablets</td><td class="r">115,485</td><td class="r">15.0%</td><td class="r">812</td><td class="r">21.3%</td><td class="r pos">+6.2%</td></tr>
<tr><td>Electronics</td><td class="r">92,388</td><td class="r">12.0%</td><td class="r">318</td><td class="r">24.1%</td><td class="r pos">+9.4%</td></tr>
<tr><td>Furniture</td><td class="r">53,893</td><td class="r">7.0%</td><td class="r">142</td><td class="r">33.2%</td><td class="r pos">+4.8%</td></tr>
<tr><td>Other</td><td class="r">30,796</td><td class="r">4.0%</td><td class="r">540</td><td class="r">38.5%</td><td class="r pos">+11.0%</td></tr>
<tr class="total"><td>Total</td><td class="r">769,900</td><td class="r">100.0%</td><td class="r">6,242</td><td class="r">27.4%</td><td class="r">+10.1%</td></tr>
</table>

<h2>Revenue Trend &mdash; Past 10 Days</h2>
<table class="dt">
<tr><th>Date</th><th class="r">Online ($)</th><th class="r">Store ($)</th><th class="r">Total ($)</th><th class="r">Orders</th><th class="r">AOV ($)</th><th class="r">DoD %</th></tr>
<tr><td>2026-05-01</td><td class="r">52,100</td><td class="r">18,900</td><td class="r">71,000</td><td class="r">445</td><td class="r">159.55</td><td class="r">&mdash;</td></tr>
<tr><td>2026-05-02</td><td class="r">55,300</td><td class="r">22,100</td><td class="r">77,400</td><td class="r">478</td><td class="r">161.92</td><td class="r pos">+9.0%</td></tr>
<tr><td>2026-05-03</td><td class="r">43,800</td><td class="r">19,600</td><td class="r">63,400</td><td class="r">389</td><td class="r">163.01</td><td class="r neg">-18.1%</td></tr>
<tr><td>2026-05-04</td><td class="r">44,200</td><td class="r">20,100</td><td class="r">64,300</td><td class="r">392</td><td class="r">164.03</td><td class="r pos">+1.4%</td></tr>
<tr><td>2026-05-05</td><td class="r">61,200</td><td class="r">24,300</td><td class="r">85,500</td><td class="r">523</td><td class="r">163.48</td><td class="r pos">+33.0%</td></tr>
<tr><td>2026-05-06</td><td class="r">59,800</td><td class="r">23,700</td><td class="r">83,500</td><td class="r">511</td><td class="r">163.40</td><td class="r neg">-2.3%</td></tr>
<tr><td>2026-05-07</td><td class="r">54,200</td><td class="r">21,800</td><td class="r">76,000</td><td class="r">467</td><td class="r">162.74</td><td class="r neg">-9.0%</td></tr>
<tr><td>2026-05-08</td><td class="r">57,400</td><td class="r">22,600</td><td class="r">80,000</td><td class="r">492</td><td class="r">162.60</td><td class="r pos">+5.3%</td></tr>
<tr><td>2026-05-09</td><td class="r">62,100</td><td class="r">24,800</td><td class="r">86,900</td><td class="r">534</td><td class="r">162.73</td><td class="r pos">+8.6%</td></tr>
<tr><td>2026-05-10</td><td class="r">58,700</td><td class="r">23,200</td><td class="r">81,900</td><td class="r">505</td><td class="r">162.18</td><td class="r neg">-5.8%</td></tr>
<tr class="total"><td>Total</td><td class="r">548,800</td><td class="r">221,100</td><td class="r">769,900</td><td class="r">4,736</td><td class="r">162.57</td><td class="r"></td></tr>
</table>

<h2>Top Products by Line &mdash; Past 10 Days</h2>
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

<h2>Regional Performance &mdash; Day &amp; MTD</h2>
<table class="dt">
<tr><th>Region</th><th class="r">Day ($)</th><th class="r">vs LW Day</th><th class="r">MTD ($)</th><th class="r">Share</th><th class="r">YoY (MTD)</th></tr>
<tr><td>North America</td><td class="r">40,950</td><td class="r pos">+28.1%</td><td class="r">384,950</td><td class="r">50.0%</td><td class="r pos">+8.4%</td></tr>
<tr><td>Europe</td><td class="r">20,475</td><td class="r pos">+31.0%</td><td class="r">192,475</td><td class="r">25.0%</td><td class="r pos">+11.2%</td></tr>
<tr><td>Asia Pacific</td><td class="r">12,285</td><td class="r pos">+34.5%</td><td class="r">115,485</td><td class="r">15.0%</td><td class="r pos">+18.7%</td></tr>
<tr><td>Latin America</td><td class="r">4,914</td><td class="r pos">+22.6%</td><td class="r">46,194</td><td class="r">6.0%</td><td class="r pos">+5.1%</td></tr>
<tr><td>Middle East</td><td class="r">2,457</td><td class="r pos">+26.0%</td><td class="r">23,097</td><td class="r">3.0%</td><td class="r pos">+14.3%</td></tr>
<tr><td>Africa</td><td class="r">819</td><td class="r pos">+30.2%</td><td class="r">7,699</td><td class="r">1.0%</td><td class="r pos">+22.1%</td></tr>
<tr class="total"><td>Total</td><td class="r">81,900</td><td class="r">+29.2%</td><td class="r">769,900</td><td class="r">100.0%</td><td class="r">+10.1%</td></tr>
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

<h2>Marketing Channel Mix &mdash; MTD</h2>
<table class="dt">
<tr><th>Channel</th><th class="r">Spend ($)</th><th class="r">Attr. Rev ($)</th><th class="r">ROAS</th><th class="r">Conv.</th></tr>
<tr><td>Email</td><td class="r">1,180</td><td class="r">9,912</td><td class="r pos">8.4x</td><td class="r">624</td></tr>
<tr><td>Google Shopping</td><td class="r">9,820</td><td class="r">50,082</td><td class="r pos">5.1x</td><td class="r">1,068</td></tr>
<tr><td>Google Search</td><td class="r">14,280</td><td class="r">59,976</td><td class="r">4.2x</td><td class="r">1,338</td></tr>
<tr><td>Display</td><td class="r">3,920</td><td class="r">14,504</td><td class="r">3.7x</td><td class="r">442</td></tr>
<tr><td>Instagram</td><td class="r">4,850</td><td class="r">15,035</td><td class="r">3.1x</td><td class="r">416</td></tr>
<tr><td>Facebook</td><td class="r">7,640</td><td class="r">21,392</td><td class="r neg">2.8x</td><td class="r">504</td></tr>
<tr class="total"><td>Total</td><td class="r">41,690</td><td class="r">170,901</td><td class="r">4.1x</td><td class="r">4,392</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Auto-generated executive summary &middot; Sources: ecomm_sales, finance_ledger, marketing_analytics &middot; Figures in USD.</div>
</div></body></html>"""
