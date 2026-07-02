# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
description = "Sales — regional performance summary (MTD through 2026-05-10)"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sales — Regional Summary</title><style>
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
<div class="hd"><h1>Sales &mdash; Regional Summary</h1>
<p class="sub">Revenue, orders and growth by region</p></div>
<p class="meta">Period: 2026-05-01 to 2026-05-10 &nbsp;|&nbsp; Generated: 2026-05-11 06:00 UTC &nbsp;|&nbsp; Source: ecomm_sales &middot; USD</p>

<h2>Highlights &mdash; MTD</h2>
<table class="kpi"><tr>
<td><span class="v">$769,900</span><span class="l">Revenue</span><span class="d pos">+10.1% YoY</span></td>
<td><span class="v">4,736</span><span class="l">Orders</span><span class="d pos">+8.6% YoY</span></td>
<td><span class="v">North America</span><span class="l">Top Region</span><span class="d pos">50.0%</span></td>
<td><span class="v">Asia Pacific</span><span class="l">Fastest Growth</span><span class="d pos">+18.7%</span></td>
</tr><tr>
<td><span class="v">$162.57</span><span class="l">Avg Order Value</span><span class="d pos">+1.4%</span></td>
<td><span class="v">6</span><span class="l">Regions</span><span class="d pos">all +YoY</span></td>
<td><span class="v">Africa</span><span class="l">Best YoY</span><span class="d pos">+22.1%</span></td>
<td><span class="v">71%</span><span class="l">Online Mix</span><span class="d pos">+1 pp</span></td>
</tr></table>
<p class="meta">Today (05-10) revenue $81,900, +29.2% vs last-week same day &nbsp;|&nbsp; YoY = vs same period FY2025</p>

<h2>Regional Performance &mdash; Day &amp; MTD</h2>
<table class="dt">
<tr><th>Region</th><th class="r">Day ($)</th><th class="r">vs LW Day</th><th class="r">MTD ($)</th><th class="r">Share</th><th class="r">Orders</th><th class="r">YoY (MTD)</th></tr>
<tr><td>North America</td><td class="r">40,950</td><td class="r pos">+28.1%</td><td class="r">384,950</td><td class="r">50.0%</td><td class="r">2,368</td><td class="r pos">+8.4%</td></tr>
<tr><td>Europe</td><td class="r">20,475</td><td class="r pos">+31.0%</td><td class="r">192,475</td><td class="r">25.0%</td><td class="r">1,184</td><td class="r pos">+11.2%</td></tr>
<tr><td>Asia Pacific</td><td class="r">12,285</td><td class="r pos">+34.5%</td><td class="r">115,485</td><td class="r">15.0%</td><td class="r">710</td><td class="r pos">+18.7%</td></tr>
<tr><td>Latin America</td><td class="r">4,914</td><td class="r pos">+22.6%</td><td class="r">46,194</td><td class="r">6.0%</td><td class="r">284</td><td class="r pos">+5.1%</td></tr>
<tr><td>Middle East</td><td class="r">2,457</td><td class="r pos">+26.0%</td><td class="r">23,097</td><td class="r">3.0%</td><td class="r">142</td><td class="r pos">+14.3%</td></tr>
<tr><td>Africa</td><td class="r">819</td><td class="r pos">+30.2%</td><td class="r">7,699</td><td class="r">1.0%</td><td class="r">48</td><td class="r pos">+22.1%</td></tr>
<tr class="total"><td>Total</td><td class="r">81,900</td><td class="r">+29.2%</td><td class="r">769,900</td><td class="r">100.0%</td><td class="r">4,736</td><td class="r">+10.1%</td></tr>
</table>

<h2>Channel Mix by Region &mdash; MTD ($)</h2>
<table class="dt">
<tr><th>Region</th><th class="r">Online</th><th class="r">Store</th><th class="r">Online %</th><th class="r">AOV ($)</th></tr>
<tr><td>North America</td><td class="r">269,465</td><td class="r">115,485</td><td class="r">70.0%</td><td class="r">162.55</td></tr>
<tr><td>Europe</td><td class="r">140,507</td><td class="r">51,968</td><td class="r">73.0%</td><td class="r">162.56</td></tr>
<tr><td>Asia Pacific</td><td class="r">87,769</td><td class="r">27,716</td><td class="r">76.0%</td><td class="r">162.65</td></tr>
<tr><td>Latin America</td><td class="r">31,212</td><td class="r">14,982</td><td class="r">67.6%</td><td class="r">162.65</td></tr>
<tr><td>Middle East</td><td class="r">15,388</td><td class="r">7,709</td><td class="r">66.6%</td><td class="r">162.65</td></tr>
<tr><td>Africa</td><td class="r">4,459</td><td class="r">3,240</td><td class="r">57.9%</td><td class="r">160.40</td></tr>
<tr class="total"><td>Total</td><td class="r">548,800</td><td class="r">221,100</td><td class="r">71.3%</td><td class="r">162.57</td></tr>
</table>

<h2>Daily Revenue by Region &mdash; Past 10 Days ($)</h2>
<table class="dt">
<tr><th>Date</th><th class="r">N.America</th><th class="r">Europe</th><th class="r">APAC</th><th class="r">Other</th><th class="r">Total</th></tr>
<tr><td>2026-05-01</td><td class="r">35,500</td><td class="r">17,750</td><td class="r">10,650</td><td class="r">7,100</td><td class="r">71,000</td></tr>
<tr><td>2026-05-02</td><td class="r">38,700</td><td class="r">19,350</td><td class="r">11,610</td><td class="r">7,740</td><td class="r">77,400</td></tr>
<tr><td>2026-05-03</td><td class="r">31,700</td><td class="r">15,850</td><td class="r">9,510</td><td class="r">6,340</td><td class="r">63,400</td></tr>
<tr><td>2026-05-04</td><td class="r">32,150</td><td class="r">16,075</td><td class="r">9,645</td><td class="r">6,430</td><td class="r">64,300</td></tr>
<tr><td>2026-05-05</td><td class="r">42,750</td><td class="r">21,375</td><td class="r">12,825</td><td class="r">8,550</td><td class="r">85,500</td></tr>
<tr><td>2026-05-06</td><td class="r">41,750</td><td class="r">20,875</td><td class="r">12,525</td><td class="r">8,350</td><td class="r">83,500</td></tr>
<tr><td>2026-05-07</td><td class="r">38,000</td><td class="r">19,000</td><td class="r">11,400</td><td class="r">7,600</td><td class="r">76,000</td></tr>
<tr><td>2026-05-08</td><td class="r">40,000</td><td class="r">20,000</td><td class="r">12,000</td><td class="r">8,000</td><td class="r">80,000</td></tr>
<tr><td>2026-05-09</td><td class="r">43,450</td><td class="r">21,725</td><td class="r">13,035</td><td class="r">8,690</td><td class="r">86,900</td></tr>
<tr><td>2026-05-10</td><td class="r">40,950</td><td class="r">20,475</td><td class="r">12,285</td><td class="r">8,190</td><td class="r">81,900</td></tr>
<tr class="total"><td>Total</td><td class="r">384,950</td><td class="r">192,475</td><td class="r">115,485</td><td class="r">76,990</td><td class="r">769,900</td></tr>
</table>

<h2>Top Products by Line &amp; Region &mdash; MTD ($)</h2>
<table class="cols"><tr>
<td><h3>A &middot; Laptops</h3>
<table class="dt">
<tr><th>Region</th><th class="r">Rev ($)</th></tr>
<tr><td>N. America</td><td class="r">153,980</td></tr>
<tr><td>Europe</td><td class="r">76,990</td></tr>
<tr><td>APAC</td><td class="r">46,194</td></tr>
<tr><td>RoW</td><td class="r">30,796</td></tr>
<tr class="total"><td>Total</td><td class="r">307,960</td></tr>
</table></td>
<td><h3>B &middot; Accessories</h3>
<table class="dt">
<tr><th>Region</th><th class="r">Rev ($)</th></tr>
<tr><td>N. America</td><td class="r">84,689</td></tr>
<tr><td>Europe</td><td class="r">42,345</td></tr>
<tr><td>APAC</td><td class="r">25,407</td></tr>
<tr><td>RoW</td><td class="r">16,937</td></tr>
<tr class="total"><td>Total</td><td class="r">169,378</td></tr>
</table></td>
<td><h3>C &middot; Tablets</h3>
<table class="dt">
<tr><th>Region</th><th class="r">Rev ($)</th></tr>
<tr><td>N. America</td><td class="r">57,743</td></tr>
<tr><td>Europe</td><td class="r">28,871</td></tr>
<tr><td>APAC</td><td class="r">17,323</td></tr>
<tr><td>RoW</td><td class="r">11,548</td></tr>
<tr class="total"><td>Total</td><td class="r">115,485</td></tr>
</table></td>
</tr></table>

<h2>Regional Growth &mdash; MTD vs LY</h2>
<table class="dt">
<tr><th>Region</th><th class="r">MTD ($)</th><th class="r">LY Same Period ($)</th><th class="r">YoY %</th><th class="r">YoY $ Δ</th></tr>
<tr><td>North America</td><td class="r">384,950</td><td class="r">355,120</td><td class="r pos">+8.4%</td><td class="r pos">+29,830</td></tr>
<tr><td>Europe</td><td class="r">192,475</td><td class="r">173,090</td><td class="r pos">+11.2%</td><td class="r pos">+19,385</td></tr>
<tr><td>Asia Pacific</td><td class="r">115,485</td><td class="r">97,290</td><td class="r pos">+18.7%</td><td class="r pos">+18,195</td></tr>
<tr><td>Latin America</td><td class="r">46,194</td><td class="r">43,952</td><td class="r pos">+5.1%</td><td class="r pos">+2,242</td></tr>
<tr><td>Middle East</td><td class="r">23,097</td><td class="r">20,207</td><td class="r pos">+14.3%</td><td class="r pos">+2,890</td></tr>
<tr><td>Africa</td><td class="r">7,699</td><td class="r">6,305</td><td class="r pos">+22.1%</td><td class="r pos">+1,394</td></tr>
<tr class="total"><td>Total</td><td class="r">769,900</td><td class="r">695,964</td><td class="r">+10.1%</td><td class="r">+73,936</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Source: ecomm_sales &middot; LW = last-week same day, LY = last-year same period &middot; USD.</div>
</div></body></html>"""
