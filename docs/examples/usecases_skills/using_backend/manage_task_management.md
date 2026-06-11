<operator/action/doc/skill done>

You are an AI data engineer, lets write a manage at scale folder, and a use case of how 1000s of jobs can be backfilled with 1 click using an git to task action by setting the date at import time, or by using the reschedule action, also write about how dependency work 

Context:
 - /Users/ganesh/Desktop/LeastAction/backend/onboarding_setup/actions/LeastActionLabs/LeastActionCheckIfParentsAreDone.py ## the dependency action that comes, user can write thier own update
   - this action is just an example, what an action can do is upto the users imagination, a action to run child task, an action to rerun all child task an action to skip all child task, add more examples that are common
 - Catalog API - LeastAction/frontend/src/services/catalog.service.ts
 - Using Catalog API - LeastAction/frontend/src/services/ai.service.ts
 - when using API to get list of items for children always send the item type, cause the item could have n, and it could be an expensive n loops to get, so folder to child folders get folder, for folder with child reports or task get them specifically.
 - This action is part of bootstrap, action can be added using config LeastAction/frontend/docs/advanced/action.md
 - also make a note of test before use, depending on what the action does it could create mess, and as always keep all the code in git to be restore and resume quickly
 - also make a note of comparision to other products, how this is so easy here, mainly cause the date is not a connected/hard coded component to the task
   - there is a table view to view all task, and action status in table view and task to see details, there is a grpagh view for all task in a workflow works based on LeastActionCheckIfParentsAreDone
   - also note dependency is based on pk name,account,project,partition so user can depend on any task in any project without complex dependecy
   - also note on how partition lets user create parallel runs of same code in same workflow or other workflows enabiling sharding and scaleing

Output:
 - location LeastAction/frontend/docs/examples/
 - add a folder to with appropriate name
 - format md
 - Expand on any of context and also mention use existing example to learn how to create actions that can do this, if context does not have specifics.
 - Don't add info to other links as the final rendering is done by react 
 - target audience AI data engineer building for leadership, name the folder and title for blog kind of post

Examples:
 - LeastAction/frontend/docs/
 - LeastAction/backend/bootstrap/ideas/UseCase Skills/asset_ui_actions_reporting.md

