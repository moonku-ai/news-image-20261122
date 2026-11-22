"""Tests for news-image-20261122 v1 — "THE WORLD IN SEVEN FRAMES".

TDD: these tests were written BEFORE main.py. Run with:
    python3 -m unittest test_main -v
from the repo directory.
"""
import ast
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)


def run_main(out_dir):
    env = dict(os.environ)
    env["MAKEFUN_OUTPUT_DIR"] = out_dir
    return subprocess.run(
        [sys.executable, os.path.join(REPO, "main.py")],
        env=env, capture_output=True, text=True, timeout=120,
    )


def read_png_chunks(path):
    with open(path, "rb") as fh:
        data = fh.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "bad PNG signature"
    pos = 8
    chunks = []
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        chunks.append((ctype, payload, crc))
        pos += 12 + length
    return data, chunks


class TestEntryPng(unittest.TestCase):
    def test_png_valid_and_sized(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = run_main(tmp)
            self.assertEqual(res.returncode, 0, res.stderr)
            path = os.path.join(tmp, "entry.png")
            self.assertTrue(os.path.exists(path), "entry.png not written")
            size = os.path.getsize(path)
            self.assertLessEqual(size, 1048576, "PNG over 1 MiB")
            self.assertGreater(size, 5000, "PNG suspiciously small")
            data, chunks = read_png_chunks(path)
            types = [c[0] for c in chunks]
            self.assertEqual(types[0], b"IHDR")
            self.assertEqual(types[-1], b"IEND")
            (w, h, depth, ctype) = struct.unpack(">IIBB", chunks[0][1][:10])
            self.assertEqual((w, h), (1024, 1024))
            self.assertEqual(depth, 8)
            self.assertEqual(ctype, 2, "must be truecolour RGB")
            for ctype_b, payload, crc in chunks:
                expect = zlib.crc32(ctype_b + payload) & 0xFFFFFFFF
                self.assertEqual(crc, expect, "bad CRC in %r" % ctype_b)
            # every IDAT payload must decompress to 1024 rows of 3073 bytes
            raw = zlib.decompress(b"".join(p for t, p, _ in chunks if t == b"IDAT"))
            self.assertEqual(len(raw), 1024 * (1 + 1024 * 3))

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            d1 = os.path.join(tmp, "a")
            d2 = os.path.join(tmp, "b")
            os.makedirs(d1)
            os.makedirs(d2)
            self.assertEqual(run_main(d1).returncode, 0)
            self.assertEqual(run_main(d2).returncode, 0)
            h1 = hashlib.sha256(open(os.path.join(d1, "entry.png"), "rb").read()).hexdigest()
            h2 = hashlib.sha256(open(os.path.join(d2, "entry.png"), "rb").read()).hexdigest()
            self.assertEqual(h1, h2, "runs are not byte-identical")

    def test_output_dir_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "nested", "out")
            res = run_main(out)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(os.path.exists(os.path.join(out, "entry.png")))


class TestFontAndLayout(unittest.TestCase):
    def test_font_covers_every_rendered_character(self):
        import main
        for text in main.ALL_TEXT:
            for ch in text:
                self.assertIn(ch, main.FONT, "font missing glyph for %r in %r" % (ch, text))

    def test_wrapped_text_fits_panels(self):
        import main
        for panel in main.PANELS:
            for block in panel["blocks"]:
                bold = block.get("bold", False)
                lines = main.wrap_text(block["text"], block["scale"], block["max_w"], bold)
                self.assertLessEqual(len(lines), block["max_lines"],
                                     "too many lines in %s: %r" % (panel["id"], block["text"]))
                for line in lines:
                    w = main.text_width(line, block["scale"], bold)
                    self.assertLessEqual(w, block["max_w"],
                                         "line too wide in %s: %r" % (panel["id"], line))
                total_h = sum(main.text_height(block["scale"]) + 4 for _ in lines) - 4
                self.assertLessEqual(total_h, block["max_h"],
                                     "text block too tall in %s" % panel["id"])

    def test_wrap_text_greedy(self):
        import main
        lines = main.wrap_text("AAA BBB CCC", 1, 42)
        self.assertEqual(lines, ["AAA BBB", "CCC"])

    def test_panels_inside_canvas(self):
        import main
        for panel in main.PANELS:
            x, y, w, h = panel["rect"]
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + w, 1024)
            self.assertLessEqual(y + h, 1024)

    def test_stdlib_only(self):
        tree = ast.parse(open(os.path.join(REPO, "main.py")).read())
        allowed = {"os", "sys", "zlib", "struct", "hashlib", "math"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertIn(a.name.split(".")[0], allowed, "non-stdlib import %s" % a.name)
            elif isinstance(node, ast.ImportFrom):
                self.assertIn((node.module or "").split(".")[0], allowed)

    def test_pictograms_draw_pixels(self):
        import main
        for name, fn in main.PICTOGRAMS.items():
            img = main.new_image(200, 200, main.BG)
            fn(img, 100, 100, 60, main.WHITE)
            px = sum(1 for row in img for p in row if p != main.BG)
            self.assertGreater(px, 200, "pictogram %s drew almost nothing" % name)

    def test_render_dimensions_and_not_blank(self):
        import main
        img = main.render()
        self.assertEqual(len(img), 1024)
        self.assertEqual(len(img[0]), 1024)
        colours = {p for row in img for p in row}
        self.assertGreater(len(colours), 12, "image looks blank/monochrome")
        self.assertIn(main.WHITE, colours)


if __name__ == "__main__":
    unittest.main()
