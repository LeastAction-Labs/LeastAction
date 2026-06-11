<doc done>

You are a AI data engineer, lets do a full email report orginization and approval workflow example under LeastAction/frontend/docs/examples/reporting_asset_management 

Context:
 - so in a company the general process we create reporting using some too and send email, while send email via reporting tool is easy, it snot always the straigh forward case, this is where leastaction can help, as a lead or admin managing least action one can create folder to orgazine the report,
 - lets say there is finance, sales, marketing, product, and sub products, all these are emails send to 10s of people too, how to go back to waht was sent or have a process check verify then a analyts sends in the case auto send from a operator is not done, likely for sensitive reports we want to check then send. 
 - This is where leastaction come to help, admin can create dev folder and business folder, and give access to only the bussiness folder in entire leastaction to business people or finance etc. 
 - Now the process would be jobs run, creates reports and add to dev folder, if approval is needed (this is done by task itself or a post action), lets say all the reports for each vertical is in finance, sales etc and in them there only pending approval reporting, and there is a UI action (ApproveAndSendReport) to approve which also sends the email to the people who are listed in the report.
 - For other auto approved reports, which all go into the business folder reports/ finance, sales, marketing, product, and sub products, here its organied by finance/ (html_report type) click leads to latest only finance/2026/02/01/ (html_report type) for past reports , the reports in the folder are managed by the ApproveAndSendReport, which only keep the latest and also add to data folder for organization
 - when using UI action, fields like task_lauis and item_lauis is auto filled based on table item selection, it will be an array.
 - for doc : this action is just an example, what an action can do is upto the users imagination


Output:
 - location LeastAction/frontend/docs/examples/reporting_asset_management
 - format md
 - Expand on any of context and also mention use existing example to learn how to create actions that can do this, if context does not have specifics.
 - Don't add info to other links as the final rendering is done by react 

Examples:
 -  LeastAction/frontend/docs/examples/postgres_sales_reporting/postgres-sales-reporting.md
 - for doc skill used in past : LeastAction/backend/bootstrap/ideas/usecases_skills_doc/asset_ui_actions_ai_reporting.md

