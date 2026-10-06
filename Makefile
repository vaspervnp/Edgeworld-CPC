PYTHON ?= python3
RASM   ?= rasm
IDSK   ?= iDSK

BUILD  := build
SRC    := $(wildcard src/*.asm)
DSK    := $(BUILD)/shield.dsk

.PHONY: all clean test

all: $(DSK)

$(BUILD):
	mkdir -p $@

assets/testplanet.png: tools/gen_testplanet.py tools/cpcpal.py
	$(PYTHON) tools/gen_testplanet.py $@

$(BUILD)/testplanet.inc: assets/testplanet.png tools/png2tiles.py tools/cpcpal.py | $(BUILD)
	$(PYTHON) tools/png2tiles.py $< $(BUILD)/testplanet

$(BUILD)/shield.bin: $(SRC) $(BUILD)/testplanet.inc
	$(RASM) src/main.asm -ob $(BUILD)/shield.bin -s -sa -os $(BUILD)/shield.sym

$(DSK): $(BUILD)/shield.bin
	rm -f $@
	$(IDSK) $@ -n
	$(IDSK) $@ -i $< -t 1 -c 0200 -e 0200

test: $(DSK)
	$(PYTHON) tests/test_scroll.py

clean:
	rm -rf $(BUILD)
