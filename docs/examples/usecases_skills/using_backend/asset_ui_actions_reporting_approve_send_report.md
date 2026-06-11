<Pending action creation, doc done>

You are an AI data engineer creating an action, lets do a full email report approval/send email workflow action

Context:
 - LeastAction/config/AI/action.txt
 - Examples provide how to use API and structure of code built using LeastAction/config/AI/action.txt and prompt
 - LeastAction/backend/bootstrap/ideas/usecases_skills_doc/asset_ui_actions_reporting.md
 - connection will contain the username password of smtp server and url and other things 
 - action variable will contain the folder laui to move
 - check and create folders that dont exist meaning list folder items for finance > yyyy > mm > dd if dd does not exist create it > then copy it
 - Catalog API - LeastAction/frontend/src/services/catalog.service.ts
 - Using Catalog API - LeastAction/frontend/src/services/ai.service.ts
 - when using API to get list of items for children always send the item type, cause the item could have n, and it could be an expensive n loops to get, so folder to child folders get folder, for folder with child reports or task get them specifically.
 - asset folder is of type folder.asset details of what it can contain - LeastAction/config/catalog.json
 - when using UI action, fields like task_lauis and item_lauis is auto filled based on table item selection, it will be an array.
 - for doc : this action is just an example, what an action can do is upto the users imagination

Output:
 - location LeastAction/backend/bootstrap/ideas/done/[add a folder to with appropriate name]
 - name.py i.e code block file, i need it as .py so i can test in ide, but later copy to onboarding 
 - name.connection in json
 - name.bashblock as json things to install for this to work
 - name.action_variables as json a sample for whats needed for action
 - name most likely is the file name of this skill (without the word skill), verify context.
 - copy this skill to the folder too
 - add the name of the skill used to create as comment in the code, at the header itself, so its easy find in the future.
 - Expand on any of context and also mention use existing example to learn how to create actions that can do this, if context does not have specifics.
 - update the usecases_skills_doc that is a mismatch, this skill context is the correct one.
 - update or add to LeastAction/frontend/docs/examples/reporting_asset_management that is a mismatch, this skill context is the correct one.
 - verify that docs for usecase is clear and talks in the context how to use, use the example structure, remove section that are not needed for a user facing example

Examples:
 - LeastAction/backend/bootstrap/ideas/done/AggReporting/AggReportingAction/
 - LeastAction/backend/bootstrap/ideas/done/GitToTask/
 - for doc skill used in past : LeastAction/backend/bootstrap/ideas/usecases_skills_doc/asset_ui_actions_ai_reporting.md

