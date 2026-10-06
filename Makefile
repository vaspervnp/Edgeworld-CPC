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

assets/testplanet.png assets/testplanet_fg.png &: tools/gen_testplanet.py tools/cpcpal.py
	$(PYTHON) tools/gen_testplanet.py assets/testplanet.png assets/testplanet_fg.png

$(BUILD)/testplanet.inc: assets/testplanet.png assets/testplanet_fg.png tools/png2tiles.py tools/cpcpal.py | $(BUILD)
	$(PYTHON) tools/png2tiles.py assets/testplanet.png $(BUILD)/testplanet assets/testplanet_fg.png
	cp $(BUILD)/testplanet.map $(BUILD)/planet.bank7.bin

assets/sprites.png assets/sprites.json &: tools/gen_sprites.py tools/gen_testplanet.py tools/cpcpal.py
	$(PYTHON) tools/gen_sprites.py assets/sprites.png assets/sprites.json

$(BUILD)/sprites.inc: assets/sprites.png assets/sprites.json tools/spritec.py tools/cpcpal.py | $(BUILD)
	rm -f $(BUILD)/sprites.bank*.bin
	$(PYTHON) tools/spritec.py assets/sprites.png assets/sprites.json $(BUILD)/sprites

$(BUILD)/tables.mask: tools/gen_tables.py | $(BUILD)
	$(PYTHON) tools/gen_tables.py $(BUILD)/tables

assets/hud.png: tools/gen_hud.py tools/cpcpal.py
	$(PYTHON) tools/gen_hud.py $@

$(BUILD)/hud.rle: assets/hud.png tools/png2scr.py tools/cpcpal.py | $(BUILD)
	$(PYTHON) tools/png2scr.py $< $(BUILD)/hud

$(BUILD)/shield.bin: $(SRC) $(BUILD)/testplanet.inc $(BUILD)/hud.rle $(BUILD)/sprites.inc $(BUILD)/tables.mask
	$(RASM) src/main.asm -ob $(BUILD)/shield.bin -s -sa -os $(BUILD)/shield.sym

# The disc: a BASIC loader (SHIELD.BAS) that loads the sprite banks into
# extra RAM, then runs the game (GAME.BIN).
$(DSK): $(BUILD)/shield.bin $(BUILD)/sprites.inc tools/mkdisc.py
	$(PYTHON) tools/mkdisc.py $@ $(BUILD)

test: $(DSK)
	$(PYTHON) tests/test_screen.py
	$(PYTHON) tests/test_player.py
	$(PYTHON) tests/test_generators.py
	$(PYTHON) tests/test_enemies.py

clean:
	rm -rf $(BUILD)
