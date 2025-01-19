import re

PART_REGEX = re.compile(
    r"(?P<label>[A-Z][a-zA-Z0-9]*(?:[\®\™\-]?[a-zA-Z0-9]+)*)(?=\s*:)\s*:\s*"
    r"(?P<content>.*?)(?="
    r"(?:[A-Z][a-zA-Z0-9]*(?:[\®\™\-]?[a-zA-Z0-9]+)*\s*:|$))",
    re.DOTALL,
)

FIBER_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*([^\d%,]+)", re.IGNORECASE)

WEIGHT_REGEX = re.compile(
    r"(\d+(?:\.\d+)?)\s*" r"(?:gr(?:ams?)?|g\/?m²|g\/?m2|G\/?M2|g\.?)", re.IGNORECASE
)
METADATA_DICT = {
    "brand": [
        "sorona",
        "cordura",
        "repreve",
    ],
    "made_in_france": ["fr"],
    "solution_dyed": ["solution dyed"],
    "recycled": ["recycled"],
}

METADATA_SPECS = [
        {"name": "brand", "is_bool": False},
        {"name": "made_in_france", "is_bool": True},
        {"name": "solution_dyed", "is_bool": True},
        {"name": "recycled", "is_bool": True},
    ]