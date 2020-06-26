import argparse
import sys

from pathlib import Path
from vfj import Font


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Propagate anchors in FontLab VFJ files."
    )
    parser.add_argument("input", type=Path, help="input VFJ file")
    parser.add_argument("output", type=Path, help="output VFJ file")

    options = parser.parse_args(args)
    font = Font(options.input)
    font.propagateAnchors()
    font.save(options.output)


if __name__ == "__main__":
    sys.exit(main())
