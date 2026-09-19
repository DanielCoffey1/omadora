"""Rebuild the theme-colored menu font from the checked-in logo artwork.

Development dependency: fonttools==4.65.0. No downloads or runtime dependency.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import parse_path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'assets/icons/brands.json').read_text())
target = ROOT / 'assets/fonts/OmadoraAppIcons.ttf'


def build():
    glyphs = {'.notdef': TTGlyphPen(None).glyph()}
    cmap = {}
    for slug, spec in manifest['icons'].items():
        raw = (ROOT / 'assets/icons/brands' / (slug + '.svg')).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == spec['sha256'], slug
        svg = ET.fromstring(raw)
        assert svg.attrib['viewBox'] == '0 0 24 24', slug
        pen = TTGlyphPen(None)
        outlines = TransformPen(Cu2QuPen(pen, max_err=1.0, reverse_direction=True),
                                (896 / 24, 0, 0, -896 / 24, 64, 960))
        paths = svg.findall('{http://www.w3.org/2000/svg}path')
        assert paths, slug
        for path in paths:
            assert 'transform' not in path.attrib, slug
            parse_path(path.attrib['d'], outlines)
        glyphs[slug] = pen.glyph()
        cmap[spec['codepoint']] = slug
    font = FontBuilder(1024, isTTF=True)
    font.setupGlyphOrder(list(glyphs))
    font.setupCharacterMap(cmap)
    font.setupGlyf(glyphs)
    font.setupHorizontalMetrics({name: (1024, 64) for name in glyphs})
    font.setupHorizontalHeader(ascent=1024, descent=0)
    font.setupNameTable({'familyName': manifest['family'], 'styleName': 'Regular',
                        'uniqueFontIdentifier': 'OmadoraAppIcons-Regular-1',
                        'fullName': manifest['family'], 'psName': 'OmadoraAppIcons-Regular',
                        'version': 'Version 1.000', 'licenseDescription': 'CC0-1.0; Simple Icons artwork'})
    font.setupOS2(sTypoAscender=1024, sTypoDescender=0, usWinAscent=1024, usWinDescent=0)
    font.setupPost()
    font.setupMaxp()
    font.font.recalcTimestamp = False
    font.font['head'].created = font.font['head'].modified = 3700000000
    output = io.BytesIO()
    font.save(output)
    return output.getvalue()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = build()
    if args.check:
        assert target.read_bytes() == data, 'Bundled logo font must be rebuilt'
    else:
        target.write_bytes(data)
    print(f'{len(manifest["icons"])} logos, {len(data)} bytes: {target.name}')
