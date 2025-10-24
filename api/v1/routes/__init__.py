from fastapi import APIRouter
from api.v1.routes.country_information import country_ops
api_version_one = APIRouter()

api_version_one.include_router(country_ops)
