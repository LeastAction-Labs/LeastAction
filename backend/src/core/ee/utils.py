from src.core.ee.models import Access


def transform_access(access: Access):
    access_dict = {}
    if access.owners:
        for key in access.owners:
            access_dict[f"access.owners.{key}"] = ""
    if access.editors:
        for key in access.editors:
            access_dict[f"access.editors.{key}"] = ""
    if access.viewers:
        for key in access.viewers:
            access_dict[f"access.viewers.{key}"] = ""
    return access_dict
