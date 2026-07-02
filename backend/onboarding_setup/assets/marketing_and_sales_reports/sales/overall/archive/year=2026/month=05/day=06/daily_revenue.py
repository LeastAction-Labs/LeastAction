# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
description = "Sales — daily revenue snapshot archived 2026-05-06"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sales — Daily Revenue (Archive)</title><style>
*{box-sizing:border-box}
body{margin:0;padding:16px;background:#eef0f2;font:13px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#222}
.wrap{max-width:680px;margin:0 auto;background:#fff;padding:22px 22px 26px;border:1px solid #e3e6e8;border-radius:4px}
.hd{border-bottom:3px solid #1a3a5c;padding-bottom:8px;margin-bottom:6px}
h1{font-size:18px;margin:0;color:#1a3a5c}
.sub{font-size:12px;color:#555;margin:2px 0 0}
.meta{font-size:11px;color:#999;margin:6px 0 10px}
.arch{font-size:10.5px;background:#fef3c7;border-left:3px solid #d97706;padding:6px 9px;margin:0 0 14px;color:#92400e}
h2{font-size:12px;margin:20px 0 7px;color:#1a3a5c;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #e3e6e8;padding-bottom:4px}
table{border-collapse:collapse;width:100%}
.kpi td{width:25%;padding:9px 6px;border:1px solid #eef0f2;text-align:center;vertical-align:top;background:#fafbfc}
.kpi .v{font-size:17px;font-weight:700;color:#1a3a5c;display:block;line-height:1.2}
.kpi .l{font-size:9.5px;color:#888;text-transform:uppercase;letter-spacing:.3px}
.dt th{background:#1a3a5c;color:#fff;padding:6px 8px;text-align:left;font-size:11px;white-space:nowrap}
.dt td{padding:5px 8px;border-bottom:1px solid #eef0f2;font-size:11px}
.dt td.r,.dt th.r{text-align:right}
.dt tr:nth-child(even) td{background:#f3f6f9}
.dt tr.total td{background:#1a3a5c;color:#fff;font-weight:700}
.pos{color:#1a7a3f}.neg{color:#b91c1c}
.foot{font-size:10px;color:#aaa;margin-top:18px;border-top:1px solid #eef0f2;padding-top:8px}
@media(max-width:600px){body{padding:8px}.wrap{padding:14px}.kpi td{padding:6px 3px}.kpi .v{font-size:14px}.dt th,.dt td{padding:4px 5px}}
</style></head><body><div class="wrap">
<div class="hd"><h1>Sales &mdash; Daily Revenue (Archive)</h1>
<p class="sub">Frozen revenue snapshot by channel &amp; region</p></div>
<p class="meta">Period: 2026-04-27 to 2026-05-06 &nbsp;|&nbsp; Source: ecomm_sales &middot; USD</p>
<div class="arch">&#128190; Archived snapshot &mdash; data frozen at 2026-05-06 23:59 UTC</div>

<h2>Highlights &mdash; 10-Day Window</h2>
<table class="kpi"><tr>
<td><span class="v">$734,100</span><span class="l">Revenue</span></td>
<td><span class="v">4,527</span><span class="l">Orders</span></td>
<td><span class="v">$162.16</span><span class="l">Avg Order Value</span></td>
<td><span class="v">71.0%</span><span class="l">Online Mix</span></td>
</tr></table>

<h2>Daily Revenue Trend</h2>
<table class="dt">
<tr><th>Date</th><th class="r">Online ($)</th><th class="r">Store ($)</th><th class="r">Total ($)</th><th class="r">Orders</th><th class="r">AOV ($)</th></tr>
<tr><td>2026-04-27</td><td class="r">49,100</td><td class="r">19,400</td><td class="r">68,500</td><td class="r">430</td><td class="r">159.30</td></tr>
<tr><td>2026-04-28</td><td class="r">51,800</td><td class="r">21,200</td><td class="r">73,000</td><td class="r">458</td><td class="r">159.39</td></tr>
<tr><td>2026-04-29</td><td class="r">55,600</td><td class="r">22,400</td><td class="r">78,000</td><td class="r">489</td><td class="r">159.51</td></tr>
<tr><td>2026-04-30</td><td class="r">48,200</td><td class="r">21,300</td><td class="r">69,500</td><td class="r">412</td><td class="r">168.70</td></tr>
<tr><td>2026-05-01</td><td class="r">52,100</td><td class="r">18,900</td><td class="r">71,000</td><td class="r">445</td><td class="r">159.55</td></tr>
<tr><td>2026-05-02</td><td class="r">55,300</td><td class="r">22,100</td><td class="r">77,400</td><td class="r">478</td><td class="r">161.92</td></tr>
<tr><td>2026-05-03</td><td class="r">43,800</td><td class="r">19,600</td><td class="r">63,400</td><td class="r">389</td><td class="r">163.01</td></tr>
<tr><td>2026-05-04</td><td class="r">44,200</td><td class="r">20,100</td><td class="r">64,300</td><td class="r">392</td><td class="r">164.03</td></tr>
<tr><td>2026-05-05</td><td class="r">61,200</td><td class="r">24,300</td><td class="r">85,500</td><td class="r">523</td><td class="r">163.48</td></tr>
<tr><td>2026-05-06</td><td class="r">59,800</td><td class="r">23,700</td><td class="r">83,500</td><td class="r">511</td><td class="r">163.40</td></tr>
<tr class="total"><td>Total</td><td class="r">521,100</td><td class="r">213,000</td><td class="r">734,100</td><td class="r">4,527</td><td class="r">162.16</td></tr>
</table>

<h2>Category Breakdown</h2>
<table class="dt">
<tr><th>Category</th><th class="r">Revenue ($)</th><th class="r">Share</th><th class="r">Margin %</th></tr>
<tr><td>Laptops</td><td class="r">293,640</td><td class="r">40.0%</td><td class="r">21.4%</td></tr>
<tr><td>Accessories</td><td class="r">161,502</td><td class="r">22.0%</td><td class="r">42.8%</td></tr>
<tr><td>Tablets</td><td class="r">110,115</td><td class="r">15.0%</td><td class="r">21.3%</td></tr>
<tr><td>Electronics</td><td class="r">88,092</td><td class="r">12.0%</td><td class="r">24.1%</td></tr>
<tr><td>Furniture &amp; Other</td><td class="r">80,751</td><td class="r">11.0%</td><td class="r">35.0%</td></tr>
<tr class="total"><td>Total</td><td class="r">734,100</td><td class="r">100.0%</td><td class="r">27.4%</td></tr>
</table>

<h2>Regional Breakdown</h2>
<table class="dt">
<tr><th>Region</th><th class="r">Revenue ($)</th><th class="r">Share</th><th class="r">Orders</th></tr>
<tr><td>North America</td><td class="r">367,050</td><td class="r">50.0%</td><td class="r">2,264</td></tr>
<tr><td>Europe</td><td class="r">183,525</td><td class="r">25.0%</td><td class="r">1,132</td></tr>
<tr><td>Asia Pacific</td><td class="r">110,115</td><td class="r">15.0%</td><td class="r">679</td></tr>
<tr><td>Latin America</td><td class="r">44,046</td><td class="r">6.0%</td><td class="r">272</td></tr>
<tr><td>Middle East</td><td class="r">22,023</td><td class="r">3.0%</td><td class="r">136</td></tr>
<tr><td>Africa</td><td class="r">7,341</td><td class="r">1.0%</td><td class="r">44</td></tr>
<tr class="total"><td>Total</td><td class="r">734,100</td><td class="r">100.0%</td><td class="r">4,527</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Archived sales snapshot &middot; Source: ecomm_sales &middot; Figures in USD.</div>
</div></body></html>"""
