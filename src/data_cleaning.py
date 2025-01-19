import re
import logging
from typing import Dict, Tuple, Optional, List

from src.constants import (
    PART_REGEX,
    FIBER_REGEX,
    WEIGHT_REGEX,
    METADATA_DICT,  # e.g. { "brand": ["cordura", ...], "made_in_france": ["fr"], ... }
    METADATA_SPECS
)
from fuzzywuzzy import process, fuzz

logging.basicConfig(level=logging.INFO)
import inflect



class FiberParser:
    """
    Encapsulates logic for parsing fiber composition, weight, brand extraction, etc.
    All metadata parsing is self-contained in this class.
    """

    @staticmethod
    def _remove_all_occurrences(text: str, token: str) -> Tuple[bool, str]:
        """
        Removes all occurrences (case-insensitive) of `token` followed optionally by ®, ™, or ©.
        Matches at word boundaries, e.g. \btoken[®™©]?\b

        Args:
            text: The string to clean.
            token: The token to remove.

        Returns:
            A tuple (found_any, new_text) where:
              - found_any: True if at least one occurrence was removed.
              - new_text: the updated text.
        """
        # Use re.subn to replace all occurrences and count the number of substitutions.
        pattern = rf"\b{re.escape(token)}[®™©]?\b"
        new_text, num_subs = re.subn(pattern, " ", text, flags=re.IGNORECASE)
        return (num_subs > 0, new_text)

    @classmethod
    def _apply_metadata_specs(cls, text: str) -> Dict[str, object]:
        """
        Process metadata tokens in the given text.
        For each metadata spec, iterate over its tokens, remove any occurrences,
        and update the metadata field.

        Returns a dictionary with the metadata fields plus:
          "clean_text": the remaining text after metadata tokens removal.
        """
        # Set defaults: boolean fields start as False and brand as empty.
        metadata: Dict[str, object] = {
            m["name"]: False if m["is_bool"] else "" for m in METADATA_SPECS
        }

        # Normalize input text.
        cleaned_text = text.lower().strip()

        # Process each metadata spec in order.
        for spec in METADATA_SPECS:
            field = spec["name"]
            is_bool = spec["is_bool"]
            tokens: List[str] = METADATA_DICT.get(field, [])

            # For each token, remove all its occurrences and update metadata.
            for token in tokens:
                found, cleaned_text = cls._remove_all_occurrences(cleaned_text, token)
                if found:
                    # For boolean fields, a single find is enough.
                    if is_bool:
                        metadata[field] = True
                    else:
                        # For non-boolean (e.g. brand) store the last matched token.
                        metadata[field] = token

        # Remove any leftover logo symbols and collapse extra spaces.
        cleaned_text = re.sub(r"[®™©]", " ", cleaned_text, flags=re.IGNORECASE)
        metadata["clean_text"] = " ".join(cleaned_text.split()).strip()
        return metadata

    @classmethod
    def parse_fibers_and_weight(
        cls, text: str, verbose: bool = False
    ) -> Tuple[Optional[float], Optional[str], List[Dict[str, object]]]:
        """
        Parse fibers and weight from text.

        Returns:
            (weight_value, weight_unit, fibers_list) where fibers_list is a list of dicts containing:
              - name: the cleaned fiber name.
              - brand: detected brand if any.
              - mix: percentage composition.
              - original_fiber_name: raw fiber name text.
              - made_in_france: bool.
              - solution_dyed: bool.
              - recycled: bool.
        """
        fibers: List[Dict[str, object]] = []

        # Extract fiber details using FIBER_REGEX.
        for match in FIBER_REGEX.finditer(text):
            pct_str, raw_name = match.groups()
            try:
                pct_val = float(pct_str)
            except ValueError:
                pct_val = None

            metadata = cls._apply_metadata_specs(raw_name)
            fiber_info = {
                "name": metadata["clean_text"],
                "brand": metadata["brand"],
                "mix": pct_val,
                "original_fiber_name": raw_name.strip(),
                "made_in_france": metadata["made_in_france"],
                "solution_dyed": metadata["solution_dyed"],
                "recycled": metadata["recycled"],
            }
            fibers.append(fiber_info)
            if verbose:
                logging.info(f"Parsed Fiber: {fiber_info}")

        # Extract weight from text.
        weight_value, weight_unit = cls._extract_weight(text, verbose=verbose)
        return weight_value, weight_unit, fibers

    @staticmethod
    def _extract_weight(
        text: str, verbose: bool = False
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Finds the first weight in 'text' using WEIGHT_REGEX.
        Returns (value, unit) or (None, None) if not found.
        """
        weight_match = WEIGHT_REGEX.search(text)
        if weight_match:
            w_val = float(weight_match.group(1))
            raw_unit = weight_match.group(0).lower()
            w_unit = "g/m²" if "m2" in raw_unit or "m²" in raw_unit else "g"
            if verbose:
                logging.info(f"Extracted weight: {w_val} {w_unit}")
            return w_val, w_unit
        return None, None

    @classmethod
    def parse_care_label(cls, desc: str, verbose: bool = False) -> Dict[str, List[Dict[str, object]]]:
        """
        Splits a clothing description into parts based on "Label: Content" blocks.
        Any text that does not match a labeled block (a leftover) is assigned the label "Unknown".
        
        Leftover text is common when:
        - The description starts with text before the first labeled block.
        - There is text between labeled blocks.
        - There is trailing text after the last labeled block.
        
        Returns:
            A dictionary with a key "parts" containing parsed part dictionaries with:
            - fabric_part: The label (or "Unknown" if no label).
            - weight: The weight value, or None.
            - weight_unit: The unit associated with the weight, or None.
            - fibers: A list of fiber details.
        """
        def process_text(text: str, label: str = "Unknown") -> Dict[str, object]:
            w_val, w_unit, fibers = cls.parse_fibers_and_weight(text, verbose=verbose)
            return {
                "fabric_part": label,
                "weight": w_val,
                "weight_unit": w_unit,
                "fibers": fibers,
            }

        parts = []
        last_end = 0

        for match in PART_REGEX.finditer(desc):
            # Check and process any text before this labeled block.
            if match.start() > last_end:
                leftover = desc[last_end:match.start()].strip(" ,.\n\r\t")
                if leftover:
                    parts.append(process_text(leftover))
            # Process the labeled block.
            label = match.group("label").strip()
            content = match.group("content").strip(" ,.\n\r\t")
            parts.append(process_text(content, label=label))
            last_end = match.end()

        # Process any trailing text after the last match.
        if last_end < len(desc):
            leftover = desc[last_end:].strip(" ,.\n\r\t")
            if leftover:
                parts.append(process_text(leftover))

        return {"parts": parts}



class FuzzyFiberMatcher:
    """
    Manages canonical fiber names for fuzzy matching.
    """

    def __init__(
        self, threshold: int = 90, initial_data: Optional[Dict[str, int]] = None
    ) -> None:
        """
        Args:
            threshold: The minimum score for a fuzzy match to be valid.
            initial_data: Pre-populated canonical fiber names with usage frequencies.
        """
        self.canonical_fibers: Dict[str, int] = (
            initial_data.copy() if initial_data else {}
        )
        self.threshold = threshold

    def get_canonical_fiber(self, name: str) -> str:
        """
        Fuzzy match a given fiber name against known canonical names.
        Adds it as a new entry if no match exceeds the threshold.
        """
        if not self.canonical_fibers:
            self.canonical_fibers[name] = 1
            return name

        matches = process.extract(
            name, self.canonical_fibers.keys(), limit=None, scorer=fuzz.token_sort_ratio
        )
        valid_matches = [
            (match, score) for match, score in matches if score >= self.threshold
        ]
        if valid_matches:
            best_candidate, _ = max(
                valid_matches, key=lambda x: self.canonical_fibers[x[0]]
            )
            self.canonical_fibers[best_candidate] += 1
            return best_candidate

        self.canonical_fibers[name] = 1
        return name


def normalize_fiber_name(name: str) -> str:
    """
    Normalize a fiber name by lowercasing, replacing hyphens with spaces,
    removing unwanted punctuation (except slashes), and collapsing spaces.
    """
    name = name.lower().strip().replace("-", " ")
    name = re.sub(r"[^a-z0-9\s\/]", " ", name)
    return " ".join(name.split())


def split_category_subcategory(cat_str: str) -> Tuple[str, str]:
    """
    Split a category string such as "ACCESSORY/PHONE-CASE" into its components.

    Returns:
        (category, subcategory). If no slash exists, returns (cat_str, "").
    """
    parts = cat_str.split("/", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (cat_str, "")

p = inflect.engine()
def clean_text(text: str) -> str:
    """
    Clean text by removing unwanted characters and collapsing spaces.
    """
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = " ".join(text.split()).lower()
    # remove plural forms
    singular = p.singular_noun(text)
    if singular:
        text = singular

    return text