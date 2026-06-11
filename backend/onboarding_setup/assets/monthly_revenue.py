# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
item_type = "html_report"
skill_name = "ReportExplorer/report_explorer_assistant"
description = "Monthly executive summary — cross-domain (finance, sales, marketing) for April 2026"
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Monthly Executive Summary</title><style>
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
<div class="hd"><h1>Monthly Executive Summary</h1>
<p class="sub">Company-wide performance &mdash; Sales &middot; Finance &middot; Marketing</p></div>
<p class="meta">Reporting month: April 2026 &nbsp;|&nbsp; Generated: 2026-05-02 06:00 UTC &nbsp;|&nbsp; Currency: USD</p>

<h2>Highlights &mdash; April 2026</h2>
<table class="kpi"><tr>
<td><span class="v">$2.28M</span><span class="l">Gross Revenue</span><span class="d pos">+3.2% MoM</span></td>
<td><span class="v">$2.08M</span><span class="l">Net Revenue</span><span class="d pos">+10.4% YoY</span></td>
<td><span class="v">14,050</span><span class="l">Orders</span><span class="d pos">+2.9% MoM</span></td>
<td><span class="v">$162.60</span><span class="l">Avg Order Value</span><span class="d pos">+0.3% MoM</span></td>
</tr><tr>
<td><span class="v">37.2%</span><span class="l">Gross Margin</span><span class="d pos">+0.5 pp</span></td>
<td><span class="v">13.1%</span><span class="l">Op. Margin</span><span class="d pos">+0.8 pp</span></td>
<td><span class="v">4.1x</span><span class="l">Marketing ROAS</span><span class="d pos">+0.2x</span></td>
<td><span class="v">$201.7K</span><span class="l">Net Income</span><span class="d pos">+12.6% YoY</span></td>
</tr></table>
<p class="meta">YTD 2026 gross revenue $8.61M &nbsp;|&nbsp; YTD net $7.84M &nbsp;|&nbsp; YTD YoY +12.7% &nbsp;|&nbsp; MoM = vs March 2026, YoY = vs April 2025</p>

<h2>Performance by Domain</h2>
<table class="dt">
<tr><th>Domain</th><th class="r">This Month</th><th class="r">MoM</th><th class="r">YoY</th><th class="r">Headline Metric</th></tr>
<tr><td>Sales (ecomm)</td><td class="r">$2,284,500</td><td class="r pos">+3.2%</td><td class="r pos">+10.4%</td><td class="r">AOV $162.60</td></tr>
<tr><td>Finance (P&amp;L)</td><td class="r">$2,079,000 net</td><td class="r pos">+0.5 pp GM</td><td class="r pos">+0.8 pp OM</td><td class="r">Net income $201.7K</td></tr>
<tr><td>Marketing</td><td class="r">$124,800 spend</td><td class="r pos">4.1x ROAS</td><td class="r pos">-4.1% CPA</td><td class="r">Conv. 13,176</td></tr>
</table>

<h2>Product Category Breakdown</h2>
<table class="dt">
<tr><th>Category</th><th class="r">Revenue ($)</th><th class="r">Share</th><th class="r">Units</th><th class="r">Margin %</th><th class="r">YoY</th></tr>
<tr><td>Laptops</td><td class="r">913,800</td><td class="r">40.0%</td><td class="r">653</td><td class="r">21.6%</td><td class="r pos">+8.6%</td></tr>
<tr><td>Accessories</td><td class="r">502,590</td><td class="r">22.0%</td><td class="r">12,490</td><td class="r">42.9%</td><td class="r pos">+15.1%</td></tr>
<tr><td>Tablets</td><td class="r">342,675</td><td class="r">15.0%</td><td class="r">2,410</td><td class="r">21.4%</td><td class="r pos">+6.7%</td></tr>
<tr><td>Electronics</td><td class="r">274,140</td><td class="r">12.0%</td><td class="r">944</td><td class="r">24.3%</td><td class="r pos">+9.9%</td></tr>
<tr><td>Furniture</td><td class="r">159,915</td><td class="r">7.0%</td><td class="r">421</td><td class="r">33.4%</td><td class="r pos">+5.2%</td></tr>
<tr><td>Other</td><td class="r">91,380</td><td class="r">4.0%</td><td class="r">1,602</td><td class="r">38.6%</td><td class="r pos">+11.5%</td></tr>
<tr class="total"><td>Total</td><td class="r">2,284,500</td><td class="r">100.0%</td><td class="r">18,520</td><td class="r">27.6%</td><td class="r">+10.4%</td></tr>
</table>

<h2>Revenue Trend &mdash; Past 12 Months</h2>
<table class="dt">
<tr><th>Month</th><th class="r">Gross ($)</th><th class="r">Net ($)</th><th class="r">Orders</th><th class="r">MoM %</th><th class="r">YoY %</th></tr>
<tr><td>2025-05</td><td class="r">1,985,000</td><td class="r">1,806,350</td><td class="r">12,210</td><td class="r">&mdash;</td><td class="r pos">+8.1%</td></tr>
<tr><td>2025-06</td><td class="r">2,040,000</td><td class="r">1,856,400</td><td class="r">12,540</td><td class="r pos">+2.8%</td><td class="r pos">+8.7%</td></tr>
<tr><td>2025-07</td><td class="r">2,110,000</td><td class="r">1,920,100</td><td class="r">12,970</td><td class="r pos">+3.4%</td><td class="r pos">+9.0%</td></tr>
<tr><td>2025-08</td><td class="r">2,065,000</td><td class="r">1,879,150</td><td class="r">12,690</td><td class="r neg">-2.1%</td><td class="r pos">+7.6%</td></tr>
<tr><td>2025-09</td><td class="r">2,180,000</td><td class="r">1,983,800</td><td class="r">13,400</td><td class="r pos">+5.6%</td><td class="r pos">+9.8%</td></tr>
<tr><td>2025-10</td><td class="r">2,240,000</td><td class="r">2,038,400</td><td class="r">13,770</td><td class="r pos">+2.8%</td><td class="r pos">+10.2%</td></tr>
<tr><td>2025-11</td><td class="r">2,690,000</td><td class="r">2,447,900</td><td class="r">16,540</td><td class="r pos">+20.1%</td><td class="r pos">+12.6%</td></tr>
<tr><td>2025-12</td><td class="r">2,910,000</td><td class="r">2,648,100</td><td class="r">17,890</td><td class="r pos">+8.2%</td><td class="r pos">+13.4%</td></tr>
<tr><td>2026-01</td><td class="r">2,015,000</td><td class="r">1,833,650</td><td class="r">12,390</td><td class="r neg">-30.8%</td><td class="r pos">+11.2%</td></tr>
<tr><td>2026-02</td><td class="r">2,090,000</td><td class="r">1,901,900</td><td class="r">12,850</td><td class="r pos">+3.7%</td><td class="r pos">+11.8%</td></tr>
<tr><td>2026-03</td><td class="r">2,213,000</td><td class="r">2,013,830</td><td class="r">13,610</td><td class="r pos">+5.9%</td><td class="r pos">+12.1%</td></tr>
<tr><td>2026-04</td><td class="r">2,284,500</td><td class="r">2,078,895</td><td class="r">14,050</td><td class="r pos">+3.2%</td><td class="r pos">+10.4%</td></tr>
<tr class="total"><td>12-mo Total</td><td class="r">26,822,500</td><td class="r">24,408,475</td><td class="r">164,900</td><td class="r"></td><td class="r">+10.6%</td></tr>
</table>

<h2>Top Products by Line &mdash; April 2026</h2>
<table class="cols"><tr>
<td><h3>A &middot; Laptops</h3>
<table class="dt">
<tr><th>Product</th><th class="r">Rev ($)</th></tr>
<tr><td>MacBook Air M3</td><td class="r">216,000</td></tr>
<tr><td>Dell XPS 15</td><td class="r">180,400</td></tr>
<tr><td>MacBook Pro 14"</td><td class="r">142,300</td></tr>
<tr><td>ThinkPad X1</td><td class="r">104,500</td></tr>
<tr><td>HP Spectre x360</td><td class="r">89,000</td></tr>
<tr class="total"><td>Top 5</td><td class="r">732,200</td></tr>
</table></td>
<td><h3>B &middot; Accessories</h3>
<table class="dt">
<tr><th>Product</th><th class="r">Rev ($)</th></tr>
<tr><td>Sony WH-1000XM5</td><td class="r">138,900</td></tr>
<tr><td>LG 27" Monitor</td><td class="r">109,050</td></tr>
<tr><td>Logitech MX 3</td><td class="r">78,020</td></tr>
<tr><td>USB-C Hub 7-in-1</td><td class="r">70,350</td></tr>
<tr><td>Anker 65W GaN</td><td class="r">42,100</td></tr>
<tr class="total"><td>Top 5</td><td class="r">438,420</td></tr>
</table></td>
<td><h3>C &middot; Tablets</h3>
<table class="dt">
<tr><th>Product</th><th class="r">Rev ($)</th></tr>
<tr><td>iPad Pro 12.9"</td><td class="r">135,700</td></tr>
<tr><td>iPad Air</td><td class="r">84,300</td></tr>
<tr><td>Galaxy Tab S9</td><td class="r">57,000</td></tr>
<tr><td>iPad 10th Gen</td><td class="r">38,300</td></tr>
<tr><td>Surface Pro 9</td><td class="r">27,375</td></tr>
<tr class="total"><td>Top 5</td><td class="r">342,675</td></tr>
</table></td>
</tr></table>

<h2>Regional Performance &mdash; Month &amp; YoY</h2>
<table class="dt">
<tr><th>Region</th><th class="r">This Month ($)</th><th class="r">Share</th><th class="r">LY Same Month ($)</th><th class="r">YoY %</th></tr>
<tr><td>North America</td><td class="r">1,142,250</td><td class="r">50.0%</td><td class="r">1,053,740</td><td class="r pos">+8.4%</td></tr>
<tr><td>Europe</td><td class="r">571,125</td><td class="r">25.0%</td><td class="r">513,600</td><td class="r pos">+11.2%</td></tr>
<tr><td>Asia Pacific</td><td class="r">342,675</td><td class="r">15.0%</td><td class="r">288,690</td><td class="r pos">+18.7%</td></tr>
<tr><td>Latin America</td><td class="r">137,070</td><td class="r">6.0%</td><td class="r">130,420</td><td class="r pos">+5.1%</td></tr>
<tr><td>Middle East</td><td class="r">68,535</td><td class="r">3.0%</td><td class="r">59,960</td><td class="r pos">+14.3%</td></tr>
<tr><td>Africa</td><td class="r">22,845</td><td class="r">1.0%</td><td class="r">18,710</td><td class="r pos">+22.1%</td></tr>
<tr class="total"><td>Total</td><td class="r">2,284,500</td><td class="r">100.0%</td><td class="r">2,065,120</td><td class="r">+10.4%</td></tr>
</table>

<h2>Regional &times; Top Line &mdash; April Revenue ($)</h2>
<table class="dt">
<tr><th>Region</th><th class="r">A Laptops</th><th class="r">B Accessories</th><th class="r">C Tablets</th><th class="r">YoY</th></tr>
<tr><td>North America</td><td class="r">456,900</td><td class="r">251,295</td><td class="r">171,338</td><td class="r pos">+8.1%</td></tr>
<tr><td>Europe</td><td class="r">228,450</td><td class="r">125,648</td><td class="r">85,669</td><td class="r pos">+11.6%</td></tr>
<tr><td>Asia Pacific</td><td class="r">137,070</td><td class="r">75,389</td><td class="r">51,401</td><td class="r pos">+19.0%</td></tr>
<tr><td>Rest of World</td><td class="r">91,380</td><td class="r">50,259</td><td class="r">34,267</td><td class="r pos">+13.9%</td></tr>
<tr class="total"><td>Total</td><td class="r">913,800</td><td class="r">502,590</td><td class="r">342,675</td><td class="r">+10.4%</td></tr>
</table>

<div class="foot">LeastAction &middot; ReportExplorer &middot; Auto-generated executive summary &middot; Sources: ecomm_sales, finance_ledger, marketing_analytics &middot; Figures in USD.</div>
</div></body></html>"""
