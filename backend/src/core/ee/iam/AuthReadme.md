# Authentication & Authorization System - Technical Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Authentication System](#authentication-system)
3. [JWT Token Structure](#jwt-token-structure)
4. [Authorization & Permissions](#authorization--permissions)
5. [IAM-Keto Integration](#iam-keto-integration)
6. [Security Considerations](#security-considerations)
7. [API Quick Reference](#api-quick-reference)
8. [Configuration](#configuration)

---

## Architecture Overview

This system implements a **two-tier security model**:
- **Authentication (IAM)**: JWT-based identity verification with RS256 signing
- **Authorization (Keto)**: Fine-grained access control using Ory Keto's relationship tuples

### Key Components

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI App (main.py)                                  │
│  ├─ Middleware: CORS → Session → Auth → Transaction   │
│  ├─ Routes: /auth, /group, /access, /catalog          │
│  └─ Services: UserService, GroupService, AuthService  │
└─────────────────────────────────────────────────────────┘
                    ↓                        ↓
         ┌──────────────────┐    ┌─────────────────────┐
         │  MongoDB         │    │  Ory Keto           │
         │  - users         │    │  - Relation Tuples  │
         │  - groups        │    │  - Permissions      │
         │  - refresh_tokens│    │  - Hierarchies      │
         └──────────────────┘    └─────────────────────┘
```

### Folder Structure

```
iam/
├── auth/
│   ├── api_request.py          # Request/response models for auth endpoints
│   ├── auth_code_dict.py        # In-memory auth code storage (TODO: move to Redis)
│   ├── credentials/
│   │   ├── credentials.py       # Credential type definitions
│   │   ├── external_validator.py # (Stub for external auth validation)
│   │   └── validator.py         # Credential validation dispatcher
│   └── service.py               # Core auth service (login, token creation)
├── session/
│   ├── claims.py                # JWT claims structure
│   └── service.py               # JWT generation and verification
├── user/
│   ├── repo.py                  # User data access layer
│   ├── schema.py                # User data models
│   └── service.py               # User business logic
├── refresh_token/
│   ├── repo.py                  # Refresh token storage
│   ├── schema.py                # Refresh token models
│   └── service.py               # Refresh token management
├── group/
│   ├── repo.py                  # Group data access
│   ├── schema.py                # Group models (with access control)
│   └── service.py               # Group management with Keto integration
└── linked_account/
    ├── repo.py                  # External account linking
    ├── schema.py                # Linked account models
    └── service.py               # External auth integration
```

---

## Authentication System

### User Registration Flow

**Endpoint**: `POST /api/v1/auth/signup` (backend/src/core/api/routes/auth.py)

```python
# Request
CreateUser(
    username: str,
    email: str,
    password: str  # Plain text (hashed server-side)
)

# Process (user/service.py:21-38)
1. Check duplicate username/email → 409 Conflict if exists
2. Hash password with SHA256
3. Store in MongoDB 'users' collection
4. Return user LAUI (MongoDB ObjectId as string)
```

### Login & Token Generation Flow

#### Step 1: Username/Password Authentication
**Endpoint**: `GET /api/v1/auth/login` (backend/src/core/api/routes/auth.py)

```python
# Query params
LoginRequest(username: str, password: str)

# Process (auth/service.py:91-110)
1. UserService.authenticate(username, password)
   - Retrieve user from MongoDB by username
   - Hash provided password (SHA256)
   - Compare hashes → ValueError if mismatch

2. Generate authorization code
   - Create random hex: secrets.token_hex(10)
   - Store in AuthCodeDict: {code → {user_laui}}
   - NOTE: In-memory storage (TODO: migrate to Redis)

3. Set cookies:
   - "session": encrypted user data
   - "oauth_flow": OAuth request parameters

4. Redirect to /api/v1/auth/redirect-with-code
```

#### Step 2: Token Exchange
**Endpoint**: `POST /api/v1/auth/token` (backend/src/core/api/routes/auth.py)

```python
# Request
TokenRequest(
    grant_type: "authorization_code" | "refresh_token",
    credentials: {
        code: str,  # For authorization_code grant
        # OR
        refresh_token: str  # For refresh_token grant
    }
)

# Process (auth/service.py:36-89)
if grant_type == "authorization_code":
    1. Lookup user_laui from authorization code
    2. Create refresh token (30-day expiry)
       - Generate 32-byte hex token
       - Hash with SHA256
       - Store in MongoDB refresh_tokens collection
    3. Generate JWT access token (24-hour expiry)

if grant_type == "refresh_token":
    1. Hash provided refresh token
    2. Lookup in MongoDB, check expiration
    3. Generate new JWT access token

# Response
TokenResponse(
    access_token: str,      # JWT token
    refresh_token: str | None,  # Only on authorization_code grant
    token_type: "Bearer",
    user: User              # User object
)
```

### Middleware Protection

**File**: backend/src/core/api/middleware/auth.py

```python
# Protected routes requiring authentication
PRIVATE_ROUTES = [
    "/api/v1/catalog/",
    "/api/v1/check/",
    "/api/v1/access",
    "/api/v1/group",
    "/api/v1/task",
    "/api/v1/action",
    "/api/v1/cron/"
]

# Process for each request:
1. Extract "Authorization: Bearer <token>" header
2. SessionService.verify_jwt_token(token)
   - Verify RS256 signature with public key
   - Check expiration (raises jwt.ExpiredSignatureError)
   - Extract claims
3. set_user_laui(claims.sub) → Store in request context
4. Attach claims to request.state.token_claims
5. If verification fails → 401 Unauthorized + clear cookies
```

### Authentication Flow Diagram

```
User Login Request
        ↓
GET /api/v1/auth/login?username=x&password=y
        ↓
UserService.authenticate()
 ├─ Retrieve user from MongoDB
 ├─ Hash provided password (SHA256)
 └─ Compare with stored hash
        ↓ (Success)
Generate Authorization Code
 ├─ Create random hex code
 ├─ Store in AuthCodeDict: {code → {user_laui}}
 └─ Set "oauth_flow" cookie
        ↓
GET /api/v1/auth/redirect-with-code?user_laui=...
        ↓
Look up Authorization Code
 ├─ Find user_laui from code
 └─ Create JWT Access Token
        ↓
POST /api/v1/auth/token
 ├─ Validate credentials
 ├─ SessionService.generate_access_token()
 │   └─ RS256 sign with private key
 ├─ RefreshTokenService.create_refresh_token()
 │   ├─ Generate 32-byte hex token
 │   ├─ Hash with SHA256
 │   ├─ Store in MongoDB (30-day expiry)
 │   └─ Return plain token (sent to client)
 └─ Return: access_token (JWT), refresh_token, user
        ↓
Client stores tokens
        ↓
Subsequent Requests
        ↓
GET /api/v1/group/get
Header: Authorization: Bearer <access_token>
        ↓ (auth_middleware)
SessionService.verify_jwt_token(token)
 ├─ RS256 verify with public key
 ├─ Extract claims
 ├─ Check expiration
 └─ Return AccessTokenClaims
        ↓
set_user_laui(claims.sub) → Context
        ↓
Route Handler Executes
 └─ Uses get_user_laui() from context
        ↓
Response
```

---

## JWT Token Structure

### Token Generation

**File**: backend/src/core/iam/session/service.py

#### Cryptographic Keys
```python
# RSA Key Pair (RS256 algorithm)
/backend/keys/private_key.pem  # Used for signing tokens
/backend/keys/public_key.pem   # Used for verification

# Loading keys (session/service.py:18-40)
SessionService.load_private_key()  # Read from file
SessionService.load_public_key()   # Read from file
```

#### JWT Claims Structure
```python
class AccessTokenClaims(BaseModel):
    sub: str       # Subject - user EMAIL (not LAUI)
    exp: int       # Expiration - Unix timestamp
    iat: int       # Issued at - Unix timestamp
    iss: str       # Issuer - "LeastAction-API-Org1"
    type: str      # Token type - "access" (hardcoded)

# Example token payload:
{
    "sub": "user@example.com",
    "exp": 1738281600,  # Now + 24 hours
    "iat": 1738195200,  # Current time
    "iss": "LeastAction-API-Org1",
    "type": "access"
}
```

#### Token Creation (session/service.py:42-56)
```python
def generate_access_token(user: User, expires_in_hours: int = 24) -> str:
    payload = AccessTokenClaims(
        sub=str(user.email),  # Using email as subject
        exp=int(datetime.now(UTC).timestamp()) + (expires_in_hours * 3600),
        iat=int(datetime.now(UTC).timestamp()),
        iss="LeastAction-API-Org1"
    )
    # Sign with RS256 algorithm
    return jwt.encode(payload.dict(), self.private_key, algorithm="RS256")
```

#### Token Verification (session/service.py:58-77)
```python
def verify_jwt_token(token: str) -> AccessTokenClaims:
    try:
        decoded = jwt.decode(
            token,
            self.public_key,
            algorithms=["RS256"],
            options={"verify_exp": True}  # Enforces expiration check
        )
        return AccessTokenClaims(**decoded)
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
```

### Refresh Token System

**File**: backend/src/core/iam/refresh_token/service.py

```python
# MongoDB Schema (refresh_token/schema.py)
RefreshToken(
    laui: LAUI,              # MongoDB _id
    user_laui: LAUI,         # User reference
    expires_at: datetime,    # 30 days from creation
    token_hash: str,         # SHA256 hash of token
    created_at: datetime,
    updated_at: Optional[datetime]
)

# Creation (service.py:21-41)
def create_refresh_token(user: User) -> str:
    1. Generate 32-byte random token: secrets.token_hex(32)
    2. Hash token with SHA256
    3. Store hash in MongoDB (expires_at = now + 30 days)
    4. Return PLAIN TOKEN to client (unhashed)

# Validation (service.py:43-59)
def get_refresh_token_from_token_string(token_string: str):
    1. Hash provided token with SHA256
    2. Lookup hash in MongoDB
    3. Check if expired → ValueError if true
    4. Return RefreshToken object
```

---

## Authorization & Permissions

### Core Concepts

**File**: backend/src/core/keto/schema.py

#### Namespaces
```python
Namespace = Enum(
    ITEM,   # Files, documents, catalog items
    GROUP,  # User groups
    USER    # Individual users
)
```

#### Relations (User/Group → Object)
```python
Relation = Enum(
    OWNERS,         # Full ownership rights
    EDITORS,        # Edit/modify rights
    VIEWERS,        # Read-only rights
    FALSE_PARENTS,  # Non-transitive hierarchical link
    TRUE_PARENT,    # Transitive hierarchical link
    NONE,
    ALL
)
```

#### Permissions (Computed Access Level)
```python
Permission = Enum(
    OWN,             # Owner access (can delete, edit, view)
    EDIT,            # Edit access (can edit, view)
    VIEW,            # View access (read-only)
    TRUE_PARENT_EDIT, # True parent edit permission
    DELETE,          # Delete permission
    IS_TRUE_PARENT,  # Check if true parent relationship
    NONE             # No access
)

# Hierarchy: OWN > EDIT > VIEW > NONE
```

### Relation Tuple Structure

**File**: backend/src/core/keto/schema.py:79-112

```python
RelationTuple(
    namespace: Namespace,           # ITEM, GROUP, or USER
    object: str,                    # Resource LAUI
    relation: Relation | Permission, # Type of relationship
    subject_id: Optional[str],      # Direct user LAUI (without prefix)
    subject_set: Optional[SubjectSet] # Indirect group-based access
)

# Direct User Access Example:
RelationTuple(
    namespace=ITEM,
    object="507f1f77bcf86cd799439011",  # Item ID
    relation=EDIT,
    subject_id="abc123def456"           # User ID
)
# Meaning: User abc123def456 can EDIT item 507f1f77bcf86cd799439011

# Group-Based Access Example:
RelationTuple(
    namespace=ITEM,
    object="507f1f77bcf86cd799439011",  # Item ID
    relation=EDIT,
    subject_set=SubjectSet(
        namespace=GROUP,
        object="group_456",             # Group ID
        relation=EDITORS                # Group role
    )
)
# Meaning: All EDITORS of group_456 can EDIT item 507f1f77bcf86cd799439011
```

### Permission Checking

**File**: backend/src/core/keto/access_reader.py

#### Basic Access Checks
```python
# Item Permissions (access_reader.py:44-93)
async def check_item_view_access(item_laui: str, user_laui: str):
    """Raises AuthorizationError if user cannot view item"""

async def check_item_edit_access(item_laui: str, user_laui: str):
    """Raises AuthorizationError if user cannot edit item"""

async def check_item_own_access(item_laui: str, user_laui: str):
    """Raises AuthorizationError if user is not owner"""

# Group Permissions (access_reader.py:95-143)
async def check_group_view_access(group_laui: str, user_laui: str)
async def check_group_edit_access(group_laui: str, user_laui: str)
async def check_group_own_access(group_laui: str, user_laui: str)

# Usage in GroupService (group/service.py:79)
async def get_group(self, group_laui: str) -> Group:
    user_laui = get_user_laui()  # From request context
    await self.access_reader.check_group_view_access(group_laui, user_laui)
    return await self.group_repo.find_group(group_laui)
```

#### Permission Level Retrieval
```python
# Get highest permission level (access_reader.py:145-200)
async def get_permission(
    item_laui: str,
    user_laui: Optional[str] = None,
    group_laui: Optional[str] = None,
    true_parent_permission: Optional[Permission] = None
) -> Permission:
    """
    Returns: Permission.OWN, .EDIT, .VIEW, or .NONE

    Logic:
    1. If true_parent_permission provided, return it (inherited)
    2. Check OWN permission
    3. Check EDIT permission
    4. Check VIEW permission
    5. Return NONE if no permissions found
    """

# Example usage (routes/access.py)
permission = await access_reader.get_permission(
    item_laui="507f1f77bcf86cd799439011",
    user_laui=get_user_laui()
)
# Returns: "own" | "edit" | "view" | "none"
```

### Hierarchical Item Access

**File**: backend/src/core/keto/access_reader.py:298-428

```python
# Hierarchy Types:
# TRUE_PARENT: Permission inherited from parent to all descendants
# FALSE_PARENTS: Permission NOT inherited, explicit access needed

async def _crawl_and_collect_item_permissions(
    false_child_lauis: list,        # Non-transitive children
    true_child_lauis: list,         # Transitive children
    accumulated_relations: list,    # Results accumulator
    user_laui: str,
    inherited_permission: Permission # From true parent
):
    """
    Recursively crawls item hierarchy:

    For TRUE children:
        - Inherit parent's permission
        - Recursively check their children

    For FALSE children:
        - Check explicit permission (no inheritance)
        - Don't recurse into their children
    """

# Example hierarchy:
# Folder A (user has OWN)
#   ├─ File B (TRUE_PARENT → inherits OWN)
#   │   └─ File C (TRUE_PARENT → inherits OWN)
#   └─ File D (FALSE_PARENT → needs explicit permission)
```

### Keto Client HTTP Interface

**File**: backend/src/core/keto/service.py

```python
class KetoClient:
    permission_check_url: str  # $KETO_READ_URL/check
    relationships_read_url: str  # $KETO_READ_URL
    relationships_write_url: str  # $KETO_WRITE_URL/admin/relation-tuples

    # Check if permission exists (service.py:67-94)
    async def check_permission(relation_tuple: RelationTuple):
        """
        HTTP GET to Keto check endpoint
        Returns: None (success) or raises AuthorizationError (403)
        """
        response = await client.get(
            f"{self.permission_check_url}?namespace={...}&object={...}"
        )
        if response.status_code == 403:
            raise AuthorizationError("Access denied")

    # Read relations (service.py:96-134)
    async def get_relations(relation_tuple: RelationTuple):
        """Returns list of matching relation tuples"""

    # Write relations (service.py:136-168)
    async def create_relation(relation_tuple: RelationTuple)
    async def delete_relation(relation_tuple: RelationTuple)

    # Batch write (service.py:170-202)
    async def patch_relations(
        relation_tuples_with_action: list[RelationTupleWithAction]
    ):
        """
        Atomically apply multiple relation changes
        Actions: INSERT or DELETE
        """
```

---

## IAM-Keto Integration

### Access Control Flow

```
┌────────────────────────────────────────────────────┐
│ 1. Request arrives with JWT token                  │
└────────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────┐
│ 2. auth_middleware validates token                 │
│    - Verify RS256 signature                        │
│    - Check expiration                              │
│    - Extract email from 'sub' claim                │
│    - set_user_laui(email) → Store in context       │
└────────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────┐
│ 3. Route handler executes                          │
│    Example: GroupService.get_group(group_laui)     │
└────────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────┐
│ 4. Permission check                                │
│    AccessReader.check_group_view_access(           │
│        group_laui=group_laui,                      │
│        user_laui=get_user_laui()  ← From context   │
│    )                                               │
└────────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────┐
│ 5. Keto permission check                           │
│    KetoClient.check_permission(                    │
│        RelationTuple(                              │
│            namespace=GROUP,                        │
│            object=group_laui,                      │
│            relation=VIEW,                          │
│            subject_id=user_laui                    │
│        )                                           │
│    )                                               │
└────────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────┐
│ 6. HTTP GET to Keto                                │
│    GET http://keto:4466/relation-tuples/check      │
│    ?namespace=GROUP&object={laui}&relation=VIEW... │
└────────────────────────────────────────────────────┘
                     ↓
        ┌────────────┴────────────┐
        ↓                         ↓
┌──────────────┐         ┌────────────────┐
│ 200 OK       │         │ 403 Forbidden  │
│ (Allowed)    │         │ (Denied)       │
└──────────────┘         └────────────────┘
        ↓                         ↓
┌──────────────┐         ┌────────────────┐
│ Continue     │         │ Raise          │
│ execution    │         │ Authorization  │
│              │         │ Error          │
└──────────────┘         └────────────────┘
```

### Access Synchronization (Write Path)

**File**: backend/src/core/keto/access_writer.py

```
MongoDB → Keto Sync Flow:

┌─────────────────────────────────────────────────────┐
│ 1. User updates group/item access via API           │
│    Example: Add user to group editors               │
└─────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 2. MongoDB change stream detects update             │
│    Field: access.editors updated                    │
└─────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 3. Event published to Redis                         │
│    Payload: {                                       │
│        item_laui: "507f...",                        │
│        action: "update",                            │
│        access_patch: {                              │
│            editors: {                               │
│                add: ["Uuser123"],                   │
│                remove: []                           │
│            }                                        │
│        }                                            │
│    }                                                │
└─────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 4. Celery worker processes event                    │
│    Task: access_writer.process_access_patch()       │
└─────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 5. Convert to Keto relation tuples                  │
│    RelationTupleWithAction(                         │
│        relation_tuple=RelationTuple(                │
│            namespace=ITEM,                          │
│            object="507f...",                        │
│            relation=EDITORS,                        │
│            subject_id="user123"                     │
│        ),                                           │
│        action=INSERT                                │
│    )                                                │
└─────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 6. Batch write to Keto                              │
│    KetoClient.patch_relations([...])                │
│    HTTP PATCH to Keto write API                     │
└─────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 7. Keto atomically applies changes                  │
│    Relations now synced with MongoDB                │
└─────────────────────────────────────────────────────┘
```

#### Access Patch Processing Details

**File**: backend/src/core/keto/access_writer.py:31-84

```python
async def process_access_patch(
    access_patch: AccessPatch,      # {owners, editors, viewers}
    object_laui: str,               # Item/Group ID
    object_namespace: Namespace     # ITEM or GROUP
):
    """
    Converts MongoDB access_patch to Keto relation tuples

    access_patch = {
        owners: {add: ["Uuser1", "Ggroup2"], remove: ["Uuser3"]},
        editors: {add: [], remove: []},
        viewers: {add: [], remove: []}
    }
    """

    relation_tuples_with_action = []

    # Process each access level
    for patch_group, relation in [
        (access_patch.owners, Relation.OWNERS),
        (access_patch.editors, Relation.EDITORS),
        (access_patch.viewers, Relation.VIEWERS)
    ]:
        # Add new access
        for subject_laui in patch_group.add:
            tuples = _get_access_relation_tuples(
                object_laui, object_namespace, subject_laui, relation
            )
            for tuple in tuples:
                relation_tuples_with_action.append(
                    RelationTupleWithAction(
                        relation_tuple=tuple,
                        action=RelationTupleAction.INSERT
                    )
                )

        # Remove access
        for subject_laui in patch_group.remove:
            # Same as above but with DELETE action

    # Atomically apply all changes
    await keto_client.patch_relations(relation_tuples_with_action)
```

#### Subject Type Handling (User vs Group)

**File**: backend/src/core/keto/access_writer.py:103-164

```python
def _get_access_relation_tuples(
    object_laui: str,
    object_namespace: Namespace,
    subject_laui: str,              # "Uuser_id" or "Ggroup_id"
    relation: Relation
) -> list[RelationTuple]:
    """
    Handles prefixed LAUIs:
    - "U" prefix = Direct user access
    - "G" prefix = Group-based access (creates 3 tuples for owners/editors/viewers)
    """

    if not subject_laui.startswith("G"):
        # Direct user access
        return [RelationTuple(
            namespace=object_namespace,
            object=object_laui,
            relation=relation,
            subject_id=subject_laui[1:]  # Remove "U" prefix
        )]

    else:
        # Group-based access
        # Need separate tuple for each group role
        group_id = subject_laui[1:]  # Remove "G" prefix
        target_relations = [
            Relation.OWNERS,
            Relation.EDITORS,
            Relation.VIEWERS
        ]

        result = []
        for group_relation in target_relations:
            result.append(RelationTuple(
                namespace=object_namespace,
                object=object_laui,
                relation=relation,
                subject_set=SubjectSet(
                    namespace=Namespace.GROUP,
                    object=group_id,
                    relation=group_relation
                )
            ))
        return result

# Example:
# Input: object_laui="item123", subject_laui="Ggroup456", relation=EDIT
# Output: [
#     RelationTuple(ITEM#item123:edit@GROUP#group456#owners),
#     RelationTuple(ITEM#item123:edit@GROUP#group456#editors),
#     RelationTuple(ITEM#item123:edit@GROUP#group456#viewers)
# ]
# Meaning: All members of group456 (owners/editors/viewers) can EDIT item123
```

### MongoDB Access Field Format

**File**: backend/src/core/iam/group/schema.py

```python
# Group/Item access field structure
access: Access = {
    "owners": {
        "Uabc123": "",      # User ID with "U" prefix
        "Ggroup456": ""     # Group ID with "G" prefix
    },
    "editors": {
        "Uxyz789": ""
    },
    "viewers": {}
}

# Key Prefixes:
# - "U" = User (direct access)
# - "G" = Group (group-based access)
# Values are empty strings (only keys matter)
```

---

## Security Considerations

### Strengths
1. **RS256 JWT**: Asymmetric signing allows public key verification
2. **Fine-grained permissions**: Keto provides flexible relation-based access control
3. **Middleware protection**: Centralized auth checking for all protected routes
4. **Token expiration**: 24-hour access tokens, 30-day refresh tokens
5. **Hierarchical access**: TRUE_PARENT enables permission inheritance

### Vulnerabilities & Recommendations

#### 1. Password Hashing (CRITICAL)
**Current**: SHA256 without salt (user/service.py:25)
```python
# INSECURE
password_hash = hashlib.sha256(password.encode()).hexdigest()
```

**Recommendation**: Use bcrypt or Argon2
```python
import bcrypt

# Hash
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Verify
if bcrypt.checkpw(provided_password.encode(), stored_hash):
    # Authenticated
```

#### 2. Authorization Code Storage (HIGH)
**Current**: In-memory dictionary (auth_code_dict.py)
```python
# Not distributed-safe
class AuthCodeDict:
    code_dict: dict[str, dict] = {}
```

**Recommendation**: Redis with TTL
```python
# Distributed and expires automatically
await redis.setex(f"auth_code:{code}", 300, user_laui)  # 5-min expiry
```

#### 3. JWT Subject Claim (MEDIUM)
**Current**: Uses email (session/service.py:47)
```python
sub=str(user.email)  # Email can change, PII in token
```

**Recommendation**: Use immutable user LAUI
```python
sub=str(user.laui)  # Immutable, non-PII identifier
```

#### 4. Token Revocation (MEDIUM)
**Issue**: No way to invalidate issued JWTs before expiration

**Recommendation**: Implement token blacklist in Redis
```python
# On logout/password change
await redis.setex(f"blacklist:{token_jti}", ttl, "1")

# In auth_middleware
if await redis.exists(f"blacklist:{claims.jti}"):
    return 401
```

#### 5. CORS Configuration (LOW)
**Current**: Allows all methods/headers from localhost:5173
```python
allow_origins=["http://localhost:5173"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"]
```

**Recommendation**: Restrict in production
```python
allow_origins=[os.getenv("FRONTEND_URL")],
allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
allow_headers=["Authorization", "Content-Type"]
```

---

## API Quick Reference

### Authentication Endpoints

**Base Path**: `/api/v1/auth`

| Method | Endpoint | Purpose | Auth Required | Request Body | Response |
|--------|----------|---------|---------------|--------------|----------|
| POST | `/signup` | Register new user | No | `CreateUser(username, email, password)` | `user_laui` (string) |
| GET | `/login` | Username/password login | No | Query: `username`, `password` | Redirect with code |
| POST | `/token` | Exchange code for JWT | No | `TokenRequest(grant_type, credentials)` | `TokenResponse(access_token, refresh_token, user)` |
| GET | `/check_frontend_token_present` | Validate session | Yes (cookie) | - | 200 OK |

### Group Endpoints

**Base Path**: `/api/v1/group`

| Method | Endpoint | Purpose | Auth Required | Request Body | Response |
|--------|----------|---------|---------------|--------------|----------|
| POST | `/create` | Create group | Yes (Bearer) | `CreateGroup(name, description, access_patch)` | `group_laui` (string) |
| GET | `/get` | List user's groups | Yes (Bearer) | Query: `relation` (OWNERS\|EDITORS\|VIEWERS) | `GroupsResponse(groups, next_page_token)` |
| GET | `/get/{laui}` | Get group details | Yes (Bearer) | Path: `group_laui` | `Group` object |
| DELETE | `/delete` | Delete group | Yes (Bearer) | Query: `group_laui` | 200 OK |

### Access Control Endpoints

**Base Path**: `/api/v1/access`

| Method | Endpoint | Purpose | Auth Required | Request Body | Response |
|--------|----------|---------|---------------|--------------|----------|
| GET | `/get/permission` | Check permission level | Yes (Bearer) | Query: `item_laui`, `subject_laui` (optional) | `{"permission": "view"\|"edit"\|"own"\|"none"}` |
| GET | `/get/users_groups` | Get hierarchical access | Yes (Bearer) | - | `AccessRelationsResponse[]` |

---

## Configuration

### Environment Variables

Required in `.env` file:

```bash
# MongoDB
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/db
MONGO_TEST_URI=mongodb://localhost:27017

# Ory Keto
KETO_READ_URL=http://localhost:4466/relation-tuples
KETO_WRITE_URL=http://localhost:4467/admin/relation-tuples/

# Redis (Celery/Access Writer)
REDIS_URL=redis://localhost:6379

# Claude API
CLAUDE_API_KEY=sk-ant-...

# Logging
LOG_LEVEL=INFO
```

### Key Files

#### RSA Key Pair Location
```
/backend/keys/
├── private_key.pem   # RSA private key (RS256 signing) - KEEP SECRET
└── public_key.pem    # RSA public key (RS256 verification) - PUBLIC
```

#### Service Initialization

**File**: backend/main.py (lines 58-135)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config = Config()
    initialize_logger(config)

    # Load JWT keys
    public_key = SessionService.load_public_key()
    private_key = SessionService.load_private_key()
    app.state.session_service = SessionService(public_key, private_key)

    # Connect to MongoDB
    database_uri = os.getenv("MONGO_URI")
    app.state.mongo_client = await create_mongo_client(database_uri)
    active_db = app.state.mongo_client.get_db("LeastActions")

    # Initialize services (dependency injection)
    app.state.user_service = UserService(...)
    app.state.auth_service = AuthService(...)
    app.state.keto_client = KetoClient()
    app.state.access_reader = AccessReader(...)
    app.state.group_service = GroupService(...)

    yield  # App runs

    # Cleanup
    await app.state.mongo_client.close_connection()
```

### Database Models

#### MongoDB Collections

**users**
```javascript
{
    _id: ObjectId,
    username: String,
    password: String (SHA256),
    email: String,
    created_at: Date
}
```

**refresh_tokens**
```javascript
{
    _id: ObjectId,
    user_laui: ObjectId,
    expires_at: Date,
    token_hash: String (SHA256),
    created_at: Date,
    updated_at: Optional<Date>
}
```

**groups**
```javascript
{
    _id: ObjectId,
    name: String,
    description: Optional<String>,
    access: {
        owners: { "<prefix><user_id>": "" },  // Prefix: "U" = user, "G" = group
        editors: { "<prefix><user_id>": "" },
        viewers: { "<prefix><user_id>": "" }
    },
    created_at: Date,
    updated_at: Optional<Date>
}
```

**linked_accounts** (OAuth Support)
```javascript
{
    _id: ObjectId,
    provider: String ("google" | "github"),
    sub: String (provider subject ID),
    user_laui: ObjectId,
    created_at: Date
}
```

---

## Context Variables

**File**: backend/src/common/user_context.py

```python
user_laui_context: ContextVar[str] = ContextVar('user_laui')

def get_user_laui() -> str:
    """Get current request's user ID from context"""
    return user_laui_context.get()

def set_user_laui(user_laui: str) -> None:
    """Set user ID for current request"""
    return user_laui_context.set(user_laui)
```

**Set by**: auth_middleware (after JWT verification)
**Used in**: GroupService, AccessReader, CatalogService, etc.

---

## Key Design Patterns

### 1. Repository Pattern
- **Files**: `user/repo.py`, `group/repo.py`, `refresh_token/repo.py`
- **Purpose**: Separate data access logic from business logic
- **Example**: `UserRepository.get_user_by_username()` abstracts MongoDB queries

### 2. Service Layer
- **Files**: `user/service.py`, `group/service.py`, `auth/service.py`
- **Purpose**: Business logic and orchestration
- **Example**: `AuthService.create_session()` coordinates credential validation + token generation

### 3. Dependency Injection
- **File**: `backend/main.py` (app.state)
- **Purpose**: Loose coupling, easier testing
- **Example**: Services injected via FastAPI `Depends(get_user_service)`

### 4. Context Variables
- **File**: `backend/src/common/user_context.py`
- **Purpose**: Thread-safe request-scoped data
- **Example**: User LAUI propagated through async call stack

### 5. Event-Driven Sync
- **Flow**: MongoDB Change Streams → Redis → Celery → Keto
- **Purpose**: Eventual consistency between MongoDB and Keto
- **Example**: Group access update triggers Keto relation tuple changes

---

## Summary

This authentication and authorization system provides:

- **Authentication**: JWT-based with RS256 signing, 24-hour access tokens, 30-day refresh tokens
- **Authorization**: Fine-grained relation-based permissions via Ory Keto
- **User Management**: Username/password authentication, refresh token rotation
- **Group Management**: RBAC with owner/editor/viewer roles
- **Hierarchical Permissions**: TRUE_PARENT (transitive) and FALSE_PARENTS (non-transitive) relationships
- **Async Architecture**: FastAPI + async/await throughout
- **Event-Driven Sync**: MongoDB changes automatically propagate to Keto via Celery

The system is designed for multi-tenant applications requiring complex, hierarchical access control with both direct user permissions and group-based permissions.
