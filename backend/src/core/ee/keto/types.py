# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Annotated

from pydantic import PlainSerializer


def replace_char(input: str):
    return input.replace("#", ".")


type KetoString = Annotated[str, PlainSerializer(replace_char, str)]
