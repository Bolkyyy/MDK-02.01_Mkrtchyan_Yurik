import os
import re
import zipfile
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMPORTS_DIR = os.path.join(BASE_DIR, "..", "imports")

FILES = ["Products_import.xlsx", "Stock_Items_import.xlsx", "Sizes_import.xlsx",
         "Orders_import.xlsx", "Users_import.xlsx"]

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group()
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - ord("A") + 1
    return n - 1


def read_shared_strings(z):
    strings = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            strings.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    return strings


def read_xlsx(path):
    with zipfile.ZipFile(path) as z:
        strings = read_shared_strings(z)
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))

    rows = []
    for row in sheet.find("m:sheetData", NS).findall("m:row", NS):
        cells = {}
        for c in row.findall("m:c", NS):
            v = c.find("m:v", NS)
            value = v.text if v is not None else ""
            if c.get("t") == "s":
                value = strings[int(value)]
            cells[col_index(c.get("r"))] = value
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return rows


def main():
    for name in FILES:
        try:
            rows = read_xlsx(os.path.join(IMPORTS_DIR, name))
        except (OSError, KeyError, zipfile.BadZipFile) as e:
            print("=== {} — ошибка чтения: {}\n".format(name, e))
            continue
        print("=== {} — строк данных: {}, колонок: {}".format(name, len(rows) - 1, len(rows[0])))
        print("Заголовок:", " | ".join(rows[0]))
        for i, row in enumerate(rows[1:4], 1):
            print("  {}: {}".format(i, " | ".join(row)))
        print()


if __name__ == "__main__":
    main()
