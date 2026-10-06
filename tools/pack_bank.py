#!/usr/bin/env python3
"""Pack files into one 16K extra RAM bank image, each at its offset.

Usage: pack_bank.py out.bin file@offset ...   (offsets in hex, e.g. map@0 logo@2000)
"""
import sys


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    bank = bytearray()
    for arg in sys.argv[2:]:
        path, offset = arg.rsplit("@", 1)
        offset = int(offset, 16)
        data = open(path, "rb").read()
        if offset < len(bank):
            raise SystemExit(f"{path} at #{offset:04X} overlaps the previous file")
        bank += bytes(offset - len(bank)) + data
    if len(bank) > 0x4000:
        raise SystemExit(f"{len(bank)} bytes do not fit a 16K bank")
    open(sys.argv[1], "wb").write(bank)


if __name__ == "__main__":
    main()
