# LeastAction Report Explorer — User Guide

## What You Get

LeastAction gives users a direct line to their data — no SQL, no tickets to engineering, no dashboards to learn. You ask a question. You get a real answer drawn from live data.

You access this through the **Report Explorer**, which you can open at login by selecting **Explorer View**.

---

## How It Works

Your data team builds pipelines and publishes **skills**. A skill is a defined AI capability: it knows what data it can access, what questions it can answer, and who is allowed to use it.

Skills are attached to folders and reports in the catalog. When you navigate to a folder or open a report, the AI chat widget automatically loads the relevant skill for that context — you don't have to select or configure anything.

You ask in plain English and get back an answer — live from the database at that moment.

**Example:**
> "What were last week's numbers by region?"

The AI runs the right query against your actual data, generates a report, and saves it to your catalog — versioned and ready to share. No BI tool, no spreadsheet export, no waiting.

---

## What You Can Ask

Anything the published skills cover. Common examples:

> "What were last week's sales numbers by region?"

> "Show me the top 10 products by revenue this month."

> "Something looks off in the Northeast numbers — send a Slack message to the sales team."

> "Email me this report."

> "Is the data for yesterday complete?"

The AI runs against live data. You get the current answer, not a cached snapshot.

---

## Reports Are Saved Automatically

Every answer is saved to your **catalog** as a report:
- Versioned — you can always see the previous answer
- Accessible to your team — anyone with the right permissions can view it
- Ready to share — no export needed

Reports live alongside the data and pipelines that produced them. If you ask the same question next week, you get a fresh answer with the latest data.

Your existing BI dashboards from Power BI, Looker, QuickSight, and Tableau are also surfaced directly in the Report Explorer — no rebuild required. They appear alongside AI-generated reports in the same folder structure, with the same permissions and the same AI chat widget available on the page.

---

## The Report Explorer

![Explorer View](../../images/Explorer-view.png)

The **Report Explorer** is where users read, navigate, and act on reports.

> **Branding tip:** The Report Explorer header logo and title are configurable in `config/system.yml` under `explore_view`. Set `logo_url` to any publicly accessible image (your company logo, a generated avatar, etc.) and `name` to whatever you want to display. Changes take effect on the next page load — no restart required.

Reports are organized into folders — by project, team, or topic — and you browse them the same way you would files.

The explorer shows all report types in the same view:

| Icon | Type | What you see |
|---|---|---|
| Document | AI-generated report | HTML report built from live data and a prompt |
| Bar chart | Power BI | Your existing Power BI dashboard, live |
| Blue insights | Looker Enterprise | Your existing Looker dashboard or look, live |
| Green insights | Looker Studio | Your existing Google Data Studio report, live |
| Pie chart | QuickSight | Your existing QuickSight dashboard, live |
| Table chart | Tableau | Your existing Tableau view or dashboard, live |

**Looker Studio vs Looker Enterprise:** Looker Studio (rebranded back to Google Data Studio) is Google's free, lightweight reporting tool for ad-hoc visualization — available to anyone with a Google account. Looker Enterprise is a separate, paid BI platform built for centralized data governance, scalable analytics, and sophisticated embeds. They share a name but are completely different products with different embed mechanisms — see your admin if you're unsure which one your team uses.

**How Looker Studio reports render:** Looker Studio does not use a backend credential exchange like the other tools. The report loads using your Google account session already in the browser. As long as you are signed into Google in your browser with an account that has been given access to that report, it renders automatically — no extra login step. If you see a "Please sign in" message, sign into Google in your browser first, then reload the page.

Embedded BI dashboards load automatically when you open them — no login to a separate tool, no context switch. For Power BI, QuickSight, Tableau, and Looker Enterprise, the embed session refreshes in the background before it expires.

When you open a report, the **AI chat widget** is available directly on the page. You don't need to leave the report to take action on what you see. From the widget you can:

- **Get Report** — pull a fresh version of this report or a related one
- **Customer Query** — ask a follow-up question about the data you're looking at
- **Run a Task** — trigger a pipeline run directly from the report context
- **Deploy Usecase** — set up a new workflow based on what you're reviewing
- **Task Status** — check whether the pipeline that produced this report is healthy
- **Send Slack / Send Email** — share findings without leaving the page
- **Run Action** — trigger a one-off action (alert, export, approval step)
- **List Tasks** — see which tasks feed into this report

The AI in the widget is context-aware — it knows which report you're viewing and which project you're in. You don't have to re-explain what you're looking at.

**What this looks like in practice:**

You open the weekly Sales report, notice revenue is down in one region, and ask:
> "Why is the Northeast number lower this week?"

The AI checks the underlying data and responds. If something looks wrong you can follow up:
> "Send a Slack message to the sales team that the Northeast numbers need a look."

Done — without leaving the report, switching tools, or filing a ticket.

---

## AI Context — Skills and the Explorer

The AI chat widget automatically loads the right skill based on where you are in the Explorer:

| Where you are | Skill loaded |
|---|---|
| Home (all projects visible) | All project-level skills — the AI can answer questions about any project |
| Inside a project folder | The skill attached to that folder and any parent folders in the hierarchy |
| Viewing a specific report | The report's own skill if it has one; otherwise inherits from the folder above it |

**The ⓘ icon** appears on project headers, folder cards, and report cards when a skill is attached. Click it to read a preview of what that skill can do — what data it knows about, what questions it's built to answer, and any limitations.

This means the AI automatically becomes more specialized as you navigate deeper. At the home screen it can answer broadly. Inside a "Sales" folder it knows the sales domain. On a specific report it knows exactly what that report shows.

You don't configure any of this — it is set up by your data team when they publish the skill and assign it to the folder or report.

> **Engineers:** For how to write actions (Slack, email, task triggers, live SQL), create skills, and wire them to folders and reports — see the [Asset Guide — Explorer Actions](/path?laui=getting-started-07-working-in-the-ui-01-assets-and-reports&itemtype=doc.file&itemname=Assets%20And%20Reports).

---

## Permissions Are Enforced

You see only what you're permitted to see. If you ask about something outside your access:

> "You don't have access to that report. Ask your admin for access to Finance Reports."

No data is leaked. Permissions are enforced at the data layer, not by hoping the AI behaves.

If you need access to something, the AI tells you exactly what to ask your admin for — and stops there.

---

## What Can I Access? — Asking the AI About Your Data

You can ask the AI directly what reports and data are available to you. This is useful when you're new to a team, or trying to find what's already been built without hunting through folders.

**Example questions:**

> "What reports are available to me?"

> "Is there a sales report for last month?"

> "What data can I ask about in the finance project?"

The AI searches the catalog with your identity and tells you exactly what it finds. If something you expect to see isn't there, it tells you who to contact or what access to request.

**What the AI can tell you:**

- Which reports are available to you and where they live
- What topics and datasets the available skills cover
- Who to ask if you need access to something you can't see

**What this is not:** The AI only sees what your account actually grants. Asking about something outside your access returns a clear denial — not the data.

---

## Two Sides of the Same Platform

| Engineer | Explorer User |
|---|---|
| Builds pipelines and operators | Asks questions about the data |
| Publishes skills backed by live data | Selects a skill and asks in plain English |
| Registers Power BI / Looker / QuickSight connections | Opens live dashboards alongside AI reports — no BI login required |
| Controls who can access what | Sees only what they're permitted to see |
| Gets alerts on failures | Gets reports and status updates |

Everything runs on your company's own infrastructure. Your data never leaves. BI credentials are held server-side and never sent to the browser.

---

## Getting Started

1. Open the **web UI** and select **Explorer View** at login
2. Navigate to your project folder or browse the home screen
3. Click the **ⓘ** icon on a folder or report to see what the AI knows about it
4. Open a report and use the **AI chat widget** to ask questions
5. Your answers appear in the catalog — versioned and shareable

If a skill you need doesn't exist yet, raise it with your data team — they can build and publish it.
