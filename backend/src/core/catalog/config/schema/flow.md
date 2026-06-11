### ## System Overview

The system's main goal is to validate incoming API data against a structure that is defined by users in JSON files, rather than being hardcoded. It works by dynamically loading a specific schema file based on an `item_type`, validating the schema itself, and then using that schema to generate a Pydantic model on-the-fly. This newly created model is then used to validate the actual request payload.

**High-Level Workflow:**

`API Request` → `Schema Manager` → `Schema Loader` → `Schema Validator` → `Model Creator` → **Dynamically Generated Pydantic Model**

---

### ## 1. ⚙️ Core Configuration (`constants_mappers`)

This module acts as a central configuration point, provlauiing essential definitions and mappings used throughout the system.

* **Purpose:** To centralize constants and avolaui hardcoding values in the logic.
* **Key Components:**
    * **`TYPES_MAPPER`**: This is a dictionary that translates the generic type names used in the user's JSON schema (e.g., "string", "array", "object") into the specific Python types that Pydantic understands (e.g., `str`, `List`, `Dict`).
    * **`SYSTEM_FIELDS`**: This is a predefined structure that defines a set of fields common to **all** `item_types`. User-defined schemas cannot overrlauie or alter these system fields, which might include attributes like `item_laui` and `created_at`.

---

### ## 2. 📜 Schema Definition (`schema_model.py`)

This module uses Pydantic to define the required structure of the user-provided `{item_type}.json` files. This ensures that any schema loaded into the system is well-formed and valid before it's used.

* **Purpose:** To create a typed, validated in-memory representation of a schema file.
* **Pydantic Models:**
    * **`ColumnModel`**: This model defines the structure for a single field within the user's schema. It includes attributes like the field's `name`, its `datatype` (chosen from a specific list of allowed types like "string" or "integer"), and a boolean `required` flag.
    * **`SchemaModel`**: This model defines the overall structure for the entire JSON schema file. It expects a list of `ColumnModel` objects for the `columns`, and lists of strings for both the `primary_keys` and `projection_fields`.

---

### ## 3. Component Breakdown: The Processing Pipeline

The following modules represent the step-by-step process of turning a user's JSON file into a usable Pydantic validation model.

#### ### i. File Loading (`schema_loader.py`)

* **Responsibility:** To find and read the specified `{item_type}.json` file from the filesystem.
* **Functionality:** It takes an `item_type` string, constructs the correct file path (e.g., `/config/schema/{item_type}.json`), and loads the file's content.
* **Error Handling:** It is designed to raise specific errors if the file is not found (`NotFoundError`) or if it's not a valid JSON file (`EncodingError`).
* **Output:** A Python dictionary containing the raw, unvalidated data from the JSON file.

#### ### ii. Schema Validation (`schema_validator.py`)

* **Responsibility:** To enforce a set of business rules on the dictionary loaded from the schema file.
* **Functionality:** This component performs two layers of validation. First, it uses the `SchemaModel` to check for basic structural correctness. Second, it runs a series of custom validation checks, such as:
    * Ensuring users have not tried to redefine a protected **system field**.
    * Verifying that all fields listed in `primary_keys` and `projection_fields` actually exist.
    * Confirming that a required string field named `"name"` is always present in the schema.
* **Error Handling:** It collects all validation failures into a detailed error report and raises a single `SchemaError` if any issues are found.

#### ### iii. Orchestration (`schema_manager.py`)

* **Responsibility:** To act as the main service layer, coordinating the loader and validator to provlauie a simple, high-level interface to the rest of the application.
* **Functionality:** Its primary method, `_get_schema_model`, calls the loader and then the validator. It is responsible for catching the `SchemaError` and converting it into a client-friendly `HTTPException` with an appropriate status code (422). It exposes clean public methods like `get_primary_keys` and `get_CreateItemRequest_model`.

#### ### iv. Model Generation (`model_creator.py`)

* **Responsibility:** To perform the final step of dynamically creating the Pydantic model class that will be used to validate the incoming API request body.
* **Functionality:** This component takes the validated `SchemaModel` as input. It starts with the predefined `SYSTEM_FIELD_SCHEMAS` and then iterates through the columns defined in the user's schema. For each column, it looks up the correct Python type using the `TYPES_MAPPER` and determines if the field is required. It assembles all these field definitions and uses Pydantic's `create_model` utility to generate a new `BaseModel` class on the fly.
* **Output:** A complete, ready-to-use Pydantic model class.