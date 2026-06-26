# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from src.core.ee.keto.schema import Permission, Relation

permission_relation_map = {
    Permission.VIEW: Relation.VIEWERS,
    Permission.EDIT: Relation.EDITORS,
    Permission.OWN: Relation.OWNERS,
    Relation.OWNERS: Permission.OWN,
    Relation.EDITORS: Permission.EDIT,
    Relation.VIEWERS: Permission.VIEW,
}

char_relations_map = {
    "V": [Relation.OWNERS, Relation.EDITORS, Relation.VIEWERS],
    "E": [Relation.OWNERS, Relation.EDITORS],
    "O": [Relation.OWNERS],
}
