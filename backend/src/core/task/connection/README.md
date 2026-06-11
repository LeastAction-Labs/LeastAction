# Connection Queue Manager

## Overview

The Connection Queue Manager module provides a sophisticated task load balancing and queuing system for managing concurrent task execution across different connections. It ensures that tasks are executed within connection-specific parallelism limits while maintaining proper ordering based on configurable sorting criteria.

## Key Components

### ConnectionQueueManager

The main class responsible for managing task queues and load balancing across connections.

#### Constructor
```python
ConnectionQueueManager(catalog_service: CatalogService)
```
- **connection_queue_repo**: Repository for database operations related to connection queues

### ConnectionQueueRepository

Repository layer handling all database operations for connection queues.

#### Constructor
```python
ConnectionQueueRepository(db: MongoDatabase)
```
- **db**: MongoDB database instance for data persistence

### Data Models

#### ConnectionQueue
Represents a task in a connection's queue.
- **name**: Task name
- **partition**: Task partition identifier
- **task_laui**: LAUI of the task 

#### ConnectionMetrics
Tracks the state and configuration of a connection's task execution.
- **max_parallelism**: Maximum number of tasks that can run concurrently for this connection
- **current_parallelism**: Current number of running tasks
- **in_queue**: Number of tasks waiting in queue
- **sort_dict**: Dictionary defining sorting criteria and order (field -> SortOrder)

#### SortOrder
Enum for sorting direction:
- **ASC**: Ascending order
- **DESC**: Descending order

## Core Functionality

### 1. Load Balancing (`load_balance_tasks`)

Main entry point for distributing incoming tasks across connections.

```python
async def load_balance_tasks(incoming_tasks: List[TaskValidationModel]) -> List[Task]
```

**Process:**
1. **Filter duplicates**: Calls `_filter_already_queued` to remove tasks that are already in the queue
2. **Group by connection**: Uses `_group_by_connection` to organize tasks by their connection_laui
3. **Enqueue new tasks**: For each connection group, calls `_enqueue_tasks` to add tasks to the queue
4. **Fetch all connections with tasks**: Retrieves all connections that have queued tasks using `get_connections_with_tasks`
5. **Pick runnable tasks**: For each connection, calls `_pick_runnable_tasks` to determine which tasks can run immediately
6. **Return runnable tasks**: Returns the list of tasks ready for execution

**Returns:** List of tasks that should be scheduled for immediate execution based on each connection's parallelism limits and sorting criteria.

### 2. Task Enqueueing (`_enqueue_task`)

Adds a task to a connection's queue with proper metrics tracking.

**Features:**
- Checks for duplicate tasks (idempotent operation)
- Updates connection metrics:
  - Increments `in_queue` counter
- Retry logic for handling concurrent updates
- Transactional integrity using `@transactional` decorator

### 3. Task Dequeueing (`dequeue_task`)

Removes a completed or cancelled task from the connection queue.

```python
async def dequeue_task(task: TaskValidationModel)
```

**Process:**
1. Locates the task in the connection queue by name and partition
2. Hard-deletes the connection_queue item
3. Updates connection metrics:
   - Decrements `current_parallelism`
4. Handles retry logic for concurrent operations
5. Raised not found error if corresponding connection_queue item not present for the task

### 4. Task Scheduling (`_get_queue_head_tasks`)

Determines which tasks should be executed based on connection limits and priorities.

**Algorithm:**
1. Calulate the parameter `available_parallelism` = `max_paralalleism` - `current_parallelism` 
2. If available parallelism is 0 then return empty list
3. Fetches all connection queues for the specified connection
4. Gets the corresponding tasks using task_laui field from the connection_queue items
5. Filter the tasks to get tasks in state QUEUED_FOR_CONNECTION 
6. Applies multi-level sorting based on `sort_dict` configuration
   - Sorts are applied in reverse order to ensure proper precedence
   - Each sort level can be ascending or descending
7. Selects top N tasks where N = `available_parallelism`

**Example:**
If `sort_dict = {"priority": DESC, "created_at": ASC}`:
- First sorts by priority (highest first)
- Then by created_at (oldest first) for tasks with same priority

## Transaction Management

The module uses transactional operations to ensure data consistency:

### `_execute_enqueue_task_transaction`
- Creates connection_queue item in catalog
- Increments connection metric `in_queue` by 1.
- Wrapped in `@transactional` decorator for rollback on failure

### `_execute_dequeue_task_transaction`
- Removes connection_queue item
- Decrements connection metric `current_parallelism`
- Ensures queue state remains consistent

### Retry Logic
Both enqueue and dequeue operations implement retry logic to handle:
- Database operation failures (`OperationFailure`)
- Concurrent modification conflicts
- Session cleanup and reset between retries
- 2-second delay between retry attempts

## Usage Flow

### Typical Task Lifecycle

1. **Task Submission**
   ```python
   tasks_to_schedule = await connection_queue_manager.load_balance_tasks(new_tasks)
   # tasks_to_schedule contains tasks ready for immediate execution
   ```

2. **Task Execution**
   - System executes the returned tasks
   - Connection's `current_parallelism` prevents over-subscription

3. **Task Completion**
   ```python
   await connection_queue_manager.dequeue_task(completed_task)
   # Frees up slot for next queued task
   ```