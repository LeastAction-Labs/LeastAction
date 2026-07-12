from pydantic import BeforeValidator
from typing import Annotated

from src.core.ee.models import Access, AccessPatch


def coerce_set_access(access_patch: dict | None):
    if access_patch is None:
        return {}  # Return empty dict which will be coerced to Access()
    return access_patch.get("add", {})


def coerce_unset_access(access_patch: dict | None):
    if access_patch is None:
        return {}  # Return empty dict which will be coerced to Access()
    return access_patch.get("remove", {})


type SetAccess = Annotated[Access, BeforeValidator(coerce_set_access)]

type UnsetAccess = Annotated[Access, BeforeValidator(coerce_unset_access)]

type AccessPatchType = AccessPatch
