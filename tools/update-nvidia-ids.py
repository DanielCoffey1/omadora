"""Regenerate factual PCI branch membership from NVIDIA's published tables."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import urlopen

URL = 'https://download.nvidia.com/XFree86/Linux-x86_64/615.71.09/README/supportedchips.html'
LEGACY_URL = 'https://download.nvidia.com/XFree86/Linux-x86_64/580.178.04/README/supportedchips.html'


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.row, self.cell = [], [], None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.tables.append([])
        elif tag == 'tr':
            self.row = []
        elif tag == 'td':
            self.cell = ''

    def handle_data(self, text):
        if self.cell is not None:
            self.cell += text

    def handle_endtag(self, tag):
        if tag == 'td':
            self.row.append(self.cell.strip())
            self.cell = None
        elif tag == 'tr' and self.row and self.tables:
            self.tables[-1].append(self.row)


if __name__ == '__main__':
    raw = urlopen(URL, timeout=60).read()
    parser = Tables()
    parser.feed(raw.decode())
    tables = [table for table in parser.tables if any(len(row) > 1 and re.fullmatch(r'[0-9A-F]{4}(?: [0-9A-F]{4}){0,2}', row[1]) for row in table)]
    result = {'source': URL, 'sha256': hashlib.sha256(raw).hexdigest(), 'branches': {}}
    # The first table is current; the next table is explicitly labelled 580.xx.
    assert 'legacy_580.xx' in raw.decode()
    for branch, table in zip(('current', '580xx'), tables[:2]):
        result['branches'][branch] = sorted({row[1].split()[0].lower() for row in table if len(row) > 1 and re.fullmatch(r'[0-9A-F]{4}(?: [0-9A-F]{4}){0,2}', row[1])})
        assert len(result['branches'][branch]) > 100
    assert not set(result['branches']['current']) & set(result['branches']['580xx'])
    legacy_raw = urlopen(LEGACY_URL, timeout=60).read()
    legacy = Tables()
    legacy.feed(legacy_raw.decode())
    legacy_tables = [table for table in legacy.tables if any(len(row) > 1 and re.fullmatch(r'[0-9A-F]{4}(?: [0-9A-F]{4}){0,2}', row[1]) for row in table)]
    result['580_source'] = LEGACY_URL
    result['580_sha256'] = hashlib.sha256(legacy_raw).hexdigest()
    result['580_supported'] = sorted({row[1].split()[0].lower() for row in legacy_tables[0] if len(row) > 1 and re.fullmatch(r'[0-9A-F]{4}(?: [0-9A-F]{4}){0,2}', row[1])})
    missing = set(result['branches']['580xx']) - set(result['580_supported'])
    # A legacy label alone is insufficient: require explicit support in 580.
    result['unverified_legacy_ids'] = sorted(missing)
    result['branches']['580xx'] = sorted(set(result['branches']['580xx']) - missing)
    target = Path(__file__).resolve().parents[1] / 'assets/nvidia-pci.json'
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print({branch: len(ids) for branch, ids in result['branches'].items()})
