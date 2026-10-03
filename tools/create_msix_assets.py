"""Generate the required Microsoft Store tile assets from Sorterino's icon."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


ASSETS = {
    "StoreLogo.png": (50, 50),
    "Square44x44Logo.png": (44, 44),
    "Square150x150Logo.png": (150, 150),
    "Square310x310Logo.png": (310, 310),
    "Wide310x150Logo.png": (310, 150),
    "SplashScreen.png": (620, 300),
}


def render(source: Path, destination: Path, canvas_size: tuple[int, int]) -> None:
    with Image.open(source) as raw:
        icon = raw.convert("RGBA")

    width, height = canvas_size
    padding = max(4, round(min(width, height) * 0.16))
    maximum = (max(1, width - padding * 2), max(1, height - padding * 2))
    icon.thumbnail(maximum, Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    position = ((width - icon.width) // 2, (height - icon.height) // 2)
    canvas.alpha_composite(icon, position)
    canvas.save(destination, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    arguments.output.mkdir(parents=True, exist_ok=True)
    for filename, size in ASSETS.items():
        render(arguments.source, arguments.output / filename, size)


if __name__ == "__main__":
    main()
