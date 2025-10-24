from pydantic import BaseModel, Field
from typing import Optional

class CountryInfo(BaseModel):
    country_name: str = Field(..., description="The name of the country")
    capital: Optional[str] = Field(None, description="The capital city of the country")
    region: Optional[str] = Field(None, description="The region where the country is located")
    population: int = Field(..., description="The population of the country")
    currency_code: str = Field(..., description="The currency code of the country")
    exchange_rate: float = Field(..., description="The country's exchange rate")
    estimated_gdp: float = Field(..., description="The estimated GDP of the country")
    flag_url: Optional[str] = Field(None, description="URL to the country's flag image")
    
    class Config:
        orm_mode = True