"""PAN plagiarism corpus loader (skeleton).

The PAN family of plagiarism datasets uses an XML annotation format
where each suspicious document has a corresponding .xml file listing
plagiarism cases with (offset, length, source_offset, source_length).

This loader handles the common subset; pass the path to the directory
containing paired .txt/.xml files. Get the corpus from
https://pan.webis.de/data.html — it requires a registration.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PANCase:
    suspicious_doc: str
    source_doc: str
    suspicious_offset: int
    suspicious_length: int
    source_offset: int
    source_length: int


def load_pan_cases(corpus_dir: str | Path) -> list[PANCase]:
    root = Path(corpus_dir)
    if not root.exists():
        raise FileNotFoundError(
            f"PAN corpus directory not found at {root}. See "
            "https://pan.webis.de/data.html"
        )
    cases: list[PANCase] = []
    for xml_path in root.glob("**/*.xml"):
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError:
            continue
        for feat in tree.getroot().findall(".//feature[@name='plagiarism']"):
            source = feat.get("source_reference")
            if not source:
                continue
            cases.append(
                PANCase(
                    suspicious_doc=xml_path.stem,
                    source_doc=Path(source).stem,
                    suspicious_offset=int(feat.get("this_offset", 0)),
                    suspicious_length=int(feat.get("this_length", 0)),
                    source_offset=int(feat.get("source_offset", 0)),
                    source_length=int(feat.get("source_length", 0)),
                )
            )
    return cases
