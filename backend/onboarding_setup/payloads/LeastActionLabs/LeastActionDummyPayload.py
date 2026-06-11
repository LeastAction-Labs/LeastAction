# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''{
    "delay_seconds": 0,
    "message": "Hello from LeastActionDummy",
    "operation": "test"
}
'''

prompt = "No-op test payload for LeastActionDummy operator. Set delay_seconds to simulate latency, message for result labelling, operation for identification."

install_docs = """# LeastActionDummyPayload — Setup

No setup required. All fields are optional and have sensible defaults.
"""

guide_docs = """# LeastActionDummyPayload — Guide

delay_seconds: sleep duration to simulate a long-running task (default 0)
message: string returned in the result output
operation: label for the operation (cosmetic only)
"""

description = "Test payload for LeastActionDummy operator — configures delay, message, and operation label for pipeline testing."

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Testing",
    "tags": ["dummy", "test", "payload", "noop"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

