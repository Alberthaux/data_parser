# models.py

from pydantic import BaseModel
from typing import List, Optional


class Fiber(BaseModel):
    product_id: str
    part_id: int
    name: str  # final cleaned name
    proportion: Optional[float]
    original_fiber_name: str = ""
    brand: str = ""  # e.g. "cordura" or "sorona"
    made_in_france: bool = False
    solution_dyed: bool = False
    recycled: bool = False


class Part(BaseModel):
    part_id: int
    product_id: str
    name: str
    weight: Optional[float] = None
    weight_unit: Optional[str] = None
    fibers: List[Fiber] = []


class Product(BaseModel):
    product_id: str
    product_category: str
    product_sub_category: str = ""
    original_care_label: str
    parts: List[Part] = []
