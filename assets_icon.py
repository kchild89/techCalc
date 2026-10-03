"""Original code-drawn shield/N icon; PNG and ICO output without image libraries."""
import base64
from pathlib import Path
import struct
import zlib


def _inside(x, y, polygon):
    result = False
    previous = polygon[-1]
    for current in polygon:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            result = not result
        previous = current
    return result


def pixels(size=64):
    outer = [(7, 6), (57, 6), (55, 39), (47, 50), (32, 60), (17, 50), (9, 39)]
    inner = [(11, 10), (53, 10), (51, 37), (44, 47), (32, 55), (20, 47), (13, 37)]
    rows = []
    for row in range(size):
        line = []
        for col in range(size):
            x, y = (col + 0.5) * 64 / size, (row + 0.5) * 64 / size
            color = (8, 13, 18, 0)
            if _inside(x, y, outer):
                color = (186, 255, 105, 255)
            if _inside(x, y, inner):
                color = (12, 23, 30, 255)
                if 18 <= x <= 23 and 18 <= y <= 41 or 41 <= x <= 46 and 18 <= y <= 41:
                    color = (230, 240, 245, 255)
                if 23 <= x <= 41 and 18 <= y <= 41 and abs(y - (18 + (x - 23) * 23 / 18)) <= 3:
                    color = (102, 217, 239, 255)
            line.append(color)
        rows.append(line)
    return rows


def png_bytes(size=64):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    data = b"".join(b"\x00" + bytes(channel for pixel in row for channel in pixel) for row in pixels(size))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(data)) + chunk(b"IEND", b""))


def icon_photo(master):
    import tkinter as tk
    return tk.PhotoImage(master=master, data=base64.b64encode(png_bytes()).decode("ascii"))


def write_icons(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "neon-hub.png").write_bytes(png_bytes(256))
    sizes = (16, 32, 48, 64, 128, 256)
    images = [png_bytes(size) for size in sizes]
    offset = 6 + len(images) * 16
    entries = []
    for size, data in zip(sizes, images):
        entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    (directory / "neon-hub.ico").write_bytes(struct.pack("<HHH", 0, 1, len(images)) + b"".join(entries) + b"".join(images))
    (directory / "neon-hub.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<path d="M7 6H57L55 39 47 50 32 60 17 50 9 39Z" fill="#baff69"/>'
        '<path d="M11 10H53L51 37 44 47 32 55 20 47 13 37Z" fill="#0c171e"/>'
        '<path d="M20.5 41V18M43.5 41V18" stroke="#e6f0f5" stroke-width="5"/>'
        '<path d="M23 18L41 41" stroke="#66d9ef" stroke-width="6"/></svg>', encoding="utf-8")


if __name__ == "__main__":
    write_icons(Path(__file__).parent / "assets")

