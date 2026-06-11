# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
description = "Sales — laptop revenue by model (MTD through 2026-05-10)"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sales — Laptop Models</title><style>
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
<div class="hd"><h1>Sales &mdash; Laptop Models</h1>
<p class="sub">Model-level revenue, units and margin</p></div>
<p class="meta">Period: 2026-05-01 to 2026-05-10 &nbsp;|&nbsp; Generated: 2026-05-11 06:00 UTC &nbsp;|&nbsp; Source: ecomm_sales &middot; USD</p>

<h2>Highlights &mdash; MTD</h2>
<table class="kpi"><tr>
<td><span class="v">$307,960</span><span class="l">Revenue</span><span class="d pos">+8.1% YoY</span></td>
<td><span class="v">207</span><span class="l">Units</span><span class="d pos">+5.4% YoY</span></td>
<td><span class="v">10</span><span class="l">Active Models</span><span class="d pos">+1 new</span></td>
<td><span class="v">$1,488</span><span class="l">Avg Price</span><span class="d pos">+2.6%</span></td>
</tr><tr>
<td><span class="v">MacBook Air M3</span><span class="l">Top Revenue</span><span class="d pos">$72.8K</span></td>
<td><span class="v">MacBook Air M3</span><span class="l">Top Units</span><span class="d pos">52</span></td>
<td><span class="v">Asus ZenBook</span><span class="l">Best Margin</span><span class="d pos">26.4%</span></td>
<td><span class="v">21.4%</span><span class="l">Avg Margin</span><span class="d pos">+0.4 pp</span></td>
</tr></table>
<p class="meta">YoY = vs same period FY2025</p>

<h2>Models Breakdown &mdash; MTD</h2>
<table class="dt">
<tr><th>#</th><th>Model</th><th>Brand</th><th class="r">Units</th><th class="r">Revenue ($)</th><th class="r">Avg Price ($)</th><th class="r">Margin %</th></tr>
<tr><td class="rank">1</td><td>MacBook Air M3</td><td>Apple</td><td class="r">52</td><td class="r">72,800</td><td class="r">1,400</td><td class="r">18.2%</td></tr>
<tr><td class="rank">2</td><td>Dell XPS 15</td><td>Dell</td><td class="r">38</td><td class="r">60,800</td><td class="r">1,600</td><td class="r">22.4%</td></tr>
<tr><td class="rank">3</td><td>MacBook Pro 14"</td><td>Apple</td><td class="r">24</td><td class="r">47,976</td><td class="r">1,999</td><td class="r">19.4%</td></tr>
<tr><td class="rank">4</td><td>ThinkPad X1 Carbon</td><td>Lenovo</td><td class="r">22</td><td class="r">35,200</td><td class="r">1,600</td><td class="r">23.7%</td></tr>
<tr><td class="rank">5</td><td>HP Spectre x360</td><td>HP</td><td class="r">20</td><td class="r">30,000</td><td class="r">1,500</td><td class="r">24.2%</td></tr>
<tr><td class="rank">6</td><td>Asus ZenBook 14</td><td>Asus</td><td class="r">18</td><td class="r">18,000</td><td class="r">1,000</td><td class="r">26.4%</td></tr>
<tr><td class="rank">7</td><td>Dell Inspiron 15</td><td>Dell</td><td class="r">18</td><td class="r">14,400</td><td class="r">800</td><td class="r">28.1%</td></tr>
<tr><td class="rank">8</td><td>Surface Laptop 5</td><td>Microsoft</td><td class="r">8</td><td class="r">11,200</td><td class="r">1,400</td><td class="r">25.3%</td></tr>
<tr><td class="rank">9</td><td>Razer Blade 15</td><td>Razer</td><td class="r">4</td><td class="r">10,120</td><td class="r">2,530</td><td class="r">20.1%</td></tr>
<tr><td class="rank">10</td><td>MSI Creator 15</td><td>MSI</td><td class="r">3</td><td class="r">7,464</td><td class="r">2,488</td><td class="r">21.8%</td></tr>
<tr class="total"><td colspan="3">Total</td><td class="r">207</td><td class="r">307,960</td><td class="r">1,488</td><td class="r">21.4%</td></tr>
</table>

<h2>Brand Summary &mdash; MTD</h2>
<table class="dt">
<tr><th>Brand</th><th class="r">Models</th><th class="r">Units</th><th class="r">Revenue ($)</th><th class="r">Share</th><th class="r">Margin %</th></tr>
<tr><td>Apple</td><td class="r">2</td><td class="r">76</td><td class="r">120,776</td><td class="r">39.2%</td><td class="r">18.6%</td></tr>
<tr><td>Dell</td><td class="r">2</td><td class="r">56</td><td class="r">75,200</td><td class="r">24.4%</td><td class="r">23.5%</td></tr>
<tr><td>Lenovo</td><td class="r">1</td><td class="r">22</td><td class="r">35,200</td><td class="r">11.4%</td><td class="r">23.7%</td></tr>
<tr><td>HP</td><td class="r">1</td><td class="r">20</td><td class="r">30,000</td><td class="r">9.7%</td><td class="r">24.2%</td></tr>
<tr><td>Asus</td><td class="r">1</td><td class="r">18</td><td class="r">18,000</td><td class="r">5.8%</td><td class="r">26.4%</td></tr>
<tr><td>Others</td><td class="r">3</td><td class="r">15</td><td class="r">28,784</td><td class="r">9.3%</td><td class="r">22.4%</td></tr>
<tr class="total"><td>Total</td><td class="r">10</td><td class="r">207</td><td class="r">307,960</td><td class="r">100.0%</td><td class="r">21.4%</td></tr>
</table>

<h2>Top Models by Brand Group &mdash; MTD</h2>
<table class="cols"><tr>
<td><h3>A &middot; Apple</h3>
<table class="dt">
<tr><th>Model</th><th class="r">Rev ($)</th></tr>
<tr><td>MacBook Air M3</td><td class="r">72,800</td></tr>
<tr><td>MacBook Pro 14"</td><td class="r">47,976</td></tr>
<tr class="total"><td>Brand</td><td class="r">120,776</td></tr>
</table></td>
<td><h3>B &middot; Dell</h3>
<table class="dt">
<tr><th>Model</th><th class="r">Rev ($)</th></tr>
<tr><td>Dell XPS 15</td><td class="r">60,800</td></tr>
<tr><td>Dell Inspiron 15</td><td class="r">14,400</td></tr>
<tr class="total"><td>Brand</td><td class="r">75,200</td></tr>
</table></td>
<td><h3>C &middot; Windows</h3>
<table class="dt">
<tr><th>Model</th><th class="r">Rev ($)</th></tr>
<tr><td>ThinkPad X1</td><td class="r">35,200</td></tr>
<tr><td>HP Spectre x360</td><td class="r">30,000</td></tr>
<tr><td>Asus ZenBook 14</td><td class="r">18,000</td></tr>
<tr class="total"><td>Group</td><td class="r">83,200</td></tr>
</table></td>
</tr></table>

<h2>Model Revenue Trend &mdash; Past 10 Days ($)</h2>
<table class="dt">
<tr><th>Date</th><th class="r">MB Air M3</th><th class="r">XPS 15</th><th class="r">MB Pro 14</th><th class="r">Others</th><th class="r">Total</th></tr>
<tr><td>2026-05-01</td><td class="r">6,720</td><td class="r">5,610</td><td class="r">4,425</td><td class="r">11,645</td><td class="r">28,400</td></tr>
<tr><td>2026-05-02</td><td class="r">7,320</td><td class="r">6,112</td><td class="r">4,824</td><td class="r">12,704</td><td class="r">30,960</td></tr>
<tr><td>2026-05-03</td><td class="r">5,996</td><td class="r">5,007</td><td class="r">3,951</td><td class="r">10,406</td><td class="r">25,360</td></tr>
<tr><td>2026-05-04</td><td class="r">6,082</td><td class="r">5,079</td><td class="r">4,008</td><td class="r">10,551</td><td class="r">25,720</td></tr>
<tr><td>2026-05-05</td><td class="r">8,086</td><td class="r">6,752</td><td class="r">5,329</td><td class="r">14,033</td><td class="r">34,200</td></tr>
<tr><td>2026-05-06</td><td class="r">7,897</td><td class="r">6,594</td><td class="r">5,204</td><td class="r">13,705</td><td class="r">33,400</td></tr>
<tr><td>2026-05-07</td><td class="r">7,187</td><td class="r">6,002</td><td class="r">4,737</td><td class="r">12,474</td><td class="r">30,400</td></tr>
<tr><td>2026-05-08</td><td class="r">7,565</td><td class="r">6,318</td><td class="r">4,986</td><td class="r">13,131</td><td class="r">32,000</td></tr>
<tr><td>2026-05-09</td><td class="r">8,217</td><td class="r">6,862</td><td class="r">5,416</td><td class="r">14,265</td><td class="r">34,760</td></tr>
<tr><td>2026-05-10</td><td class="r">7,730</td><td class="r">6,464</td><td class="r">5,096</td><td class="r">13,470</td><td class="r">32,760</td></tr>
<tr class="total"><td>Total</td><td class="r">72,800</td><td class="r">60,800</td><td class="r">47,976</td><td class="r">126,384</td><td class="r">307,960</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Source: ecomm_sales &middot; Figures in USD.</div>
</div></body></html>"""
