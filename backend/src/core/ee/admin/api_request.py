from pydantic import BaseModel


from src.core.ee.license.schema import UpdateLicense


class AdminCreateUserRequest(BaseModel):
    username: str
    email: str


class AdminLicenseUpdate(UpdateLicense):
    pass
