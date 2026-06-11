# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from collections.abc import Mapping
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

MongoDocument = Mapping[str, Any]
MongoClient = AsyncMongoClient[MongoDocument]
MongoDatabase = AsyncDatabase[MongoDocument]
MongoCollection = AsyncCollection[MongoDocument]
