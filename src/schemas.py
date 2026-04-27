from pydantic import BaseModel, Field
from typing import Optional

class PropertyInput(BaseModel):
    property_type: int = Field(..., description="Number of bedrooms (e.g., 1, 2, 3)")
    area: float = Field(..., description="Area in square feet")
    sub_area: str = Field(..., description="Location sub-area (e.g., 'kothrud', 'baner')")
    description: Optional[str] = Field(default="", description="Text description of the property")
    clubhouse: int = Field(..., description="1 if present, 0 otherwise")
    school: int = Field(..., description="1 if present, 0 otherwise")
    hospital: int = Field(..., description="1 if present, 0 otherwise")
    mall: int = Field(..., description="1 if present, 0 otherwise")
    park: int = Field(..., description="1 if present, 0 otherwise")
    pool: int = Field(..., description="1 if present, 0 otherwise")
    gym: int = Field(..., description="1 if present, 0 otherwise")

class PriceResponse(BaseModel):
    predicted_price: float
    lower_bound: float
    upper_bound: float
    features_used: int

class HealthResponse(BaseModel):
    status: str

class ModelInfoResponse(BaseModel):
    model_type: str
    vectorizer_vocab_size: int
    interval_margin: float