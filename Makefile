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

# The planets: bank images the game loads from disc (src/disc.asm).
PLANETS := 1 2
$(BUILD)/planet%.bin: assets/planets/planet%.json $(BUILD)/testplanet.inc tools/mkplanet.py tools/cpcpal.py
	$(PYTHON) tools/mkplanet.py $< $(BUILD)/testplanet $@

# Extra bank 6: the last sprites, and the title logo at #2800 (src/logo.asm).
$(BUILD)/bank6.bin: $(BUILD)/sprites.inc $(BUILD)/logo.bin tools/pack_bank.py
	$(PYTHON) tools/pack_bank.py $@ $(BUILD)/sprites.bank6.bin@0 $(BUILD)/logo.bin@2800

assets/logo.png $(BUILD)/logo.bin &: tools/gen_logo.py tools/gen_testplanet.py tools/font.py tools/cpcpal.py | $(BUILD)
	$(PYTHON) tools/gen_logo.py assets/logo.png $(BUILD)/logo.bin

$(BUILD)/font.bin: tools/font.py | $(BUILD)
	$(PYTHON) tools/font.py $@

$(BUILD)/sound.inc: tools/gen_music.py | $(BUILD)
	$(PYTHON) tools/gen_music.py $@

assets/sprites.png assets/sprites.json &: tools/gen_sprites.py tools/gen_testplanet.py tools/cpcpal.py
	$(PYTHON) tools/gen_sprites.py assets/sprites.png assets/sprites.json

$(BUILD)/sprites.inc: assets/sprites.png assets/sprites.json tools/spritec.py tools/cpcpal.py | $(BUILD)
	rm -f $(BUILD)/sprites.bank*.bin
	$(PYTHON) tools/spritec.py assets/sprites.png assets/sprites.json $(BUILD)/sprites

$(BUILD)/tables.mask: tools/gen_tables.py | $(BUILD)
	$(PYTHON) tools/gen_tables.py $(BUILD)/tables

assets/hud.png: tools/gen_hud.py tools/font.py tools/cpcpal.py
	$(PYTHON) tools/gen_hud.py $@

$(BUILD)/hud.rle: assets/hud.png tools/png2scr.py tools/cpcpal.py | $(BUILD)
	$(PYTHON) tools/png2scr.py $< $(BUILD)/hud

$(BUILD)/shield.bin: $(SRC) $(BUILD)/hud.rle $(BUILD)/sprites.inc $(BUILD)/tables.mask \
		$(BUILD)/font.bin $(BUILD)/sound.inc
	$(RASM) src/main.asm -ob $(BUILD)/shield.bin -s -sa -os $(BUILD)/shield.sym

# The disc: a BASIC loader (SHIELD.BAS) that loads the sprite banks into
# extra RAM, then runs the game (GAME.BIN).
$(DSK): $(BUILD)/shield.bin $(BUILD)/sprites.inc $(BUILD)/bank6.bin $(PLANETS:%=$(BUILD)/planet%.bin) tools/mkdisc.py
	$(PYTHON) tools/mkdisc.py $@ $(BUILD)/shield.bin BANK4=$(BUILD)/sprites.bank4.bin \
		BANK5=$(BUILD)/sprites.bank5.bin BANK6=$(BUILD)/bank6.bin \
		$(foreach p,$(PLANETS),PLANET$(p)=$(BUILD)/planet$(p).bin)

test: $(DSK)
	$(PYTHON) tests/test_screen.py
	$(PYTHON) tests/test_player.py
	$(PYTHON) tests/test_generators.py
	$(PYTHON) tests/test_enemies.py
	$(PYTHON) tests/test_game.py
	$(PYTHON) tests/test_planets.py
	$(PYTHON) tests/playtest.py idle gunner keeper

clean:
	rm -rf $(BUILD)
