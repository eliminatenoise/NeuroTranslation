"""Read a selected C2 trial's foot-to-platform codes from the article supplement."""
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

WORD = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def cell_text(cell):
    return "".join(node.text or "" for node in cell.findall(".//w:t", WORD)).strip()


class ContactTable:
    """Retain the XML privately. Decode flags only for explicitly selected trials."""

    def __init__(self, supplement_docx):
        with zipfile.ZipFile(supplement_docx) as document:
            root = ET.fromstring(document.read("word/document.xml"))
        table = root.findall("w:body/w:tbl", WORD)[1]
        rows = table.findall("w:tr", WORD)
        headers = [cell_text(c) for c in rows[1].findall("w:tc", WORD)]
        repeats = [cell_text(c) for c in rows[2].findall("w:tc", WORD)]
        if headers != ["", "C1", "C2", "C3", "C4", "C5"] or repeats[7:13] != ["01","02","03","04","05","06"]:
            raise ValueError("Supplementary Table 2 layout does not match the selected edition")
        self.rows = {cell_text(row.find("w:tc", WORD)): row for row in rows[3:]}

    def contacts(self, source_file):
        person, condition, repeat = Path(source_file).stem.split("_")
        if condition != "C2" or not 1 <= int(repeat) <= 6:
            raise ValueError("This study selected C2 repeats 01 through 06")
        if person not in self.rows:
            return {"code": None, "trial_available": None, "right_plate": None, "left_plate": None,
                    "reason": "Source participant folder has no exact match in Supplementary Table 2"}
        row = self.rows[person].findall("w:tc", WORD)
        code = cell_text(row[6 + int(repeat)])
        if code == "NA":
            return {"code": code, "trial_available": False, "right_plate": None, "left_plate": None}
        if len(code) != 2 or set(code) - {"0","1","2"}:
            raise ValueError(f"Unknown force availability code {code!r}")
        return {"code": code, "trial_available": True, "right_plate": int(code[0]) or None,
                "left_plate": int(code[1]) or None}
