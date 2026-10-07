PYTHON ?= python3
VERSION := 1.4
export VERSION
RASM   ?= rasm
IDSK   ?= iDSK

BUILD  := build
SRC    := $(wildcard src/*.asm)
DSK    := $(BUILD)/shield.dsk

.PHONY: all clean test planet-art release

all: $(DSK) planet-art

$(BUILD):
	mkdir -p $@

# The planets: art from each description (assets/planets/planetN.json),
# converted to tiles, packed into bank images the game loads from disc
# (src/disc.asm).
PLANETS := 1 2 3 4
.SECONDARY: $(PLANETS:%=assets/planet%.png) $(PLANETS:%=assets/planet%_fg.png) $(PLANETS:%=$(BUILD)/planet%.inc)
planet-art: $(PLANETS:%=assets/planet%.png)     # the tests compare the screen with it

assets/planet%.png assets/planet%_fg.png &: assets/planets/planet%.json tools/gen_planet.py tools/pens.py tools/cpcpal.py
	$(PYTHON) tools/gen_planet.py $< assets/planet$*.png assets/planet$*_fg.png

$(BUILD)/planet%.inc: assets/planet%.png assets/planet%_fg.png tools/png2tiles.py tools/cpcpal.py | $(BUILD)
	$(PYTHON) tools/png2tiles.py assets/planet$*.png $(BUILD)/planet$* assets/planet$*_fg.png

$(BUILD)/planet%.bin: assets/planets/planet%.json $(BUILD)/planet%.inc tools/mkplanet.py tools/pens.py tools/cpcpal.py
	$(PYTHON) tools/mkplanet.py $< $(BUILD)/planet$* $@

# Extra bank 6: the last sprites.
$(BUILD)/bank6.bin: $(BUILD)/sprites.inc tools/pack_bank.py
	$(PYTHON) tools/pack_bank.py $@ $(BUILD)/sprites.bank6.bin@0

assets/logo.png $(BUILD)/logo.bin &: tools/gen_logo.py tools/pens.py tools/font.py tools/cpcpal.py | $(BUILD)
	$(PYTHON) tools/gen_logo.py assets/logo.png $(BUILD)/logo.bin

$(BUILD)/font.bin: tools/font.py | $(BUILD)
	$(PYTHON) tools/font.py $@

$(BUILD)/sound.inc: tools/gen_music.py | $(BUILD)
	$(PYTHON) tools/gen_music.py $@

assets/sprites.png assets/sprites.json &: tools/gen_sprites.py tools/pens.py tools/cpcpal.py
	$(PYTHON) tools/gen_sprites.py assets/sprites.png assets/sprites.json

$(BUILD)/sprites.inc $(BUILD)/sprites.tiny &: assets/sprites.png assets/sprites.json tools/spritec.py tools/cpcpal.py | $(BUILD)
	rm -f $(BUILD)/sprites.bank*.bin
	$(PYTHON) tools/spritec.py assets/sprites.png assets/sprites.json $(BUILD)/sprites

$(BUILD)/tables.mask: tools/gen_tables.py | $(BUILD)
	$(PYTHON) tools/gen_tables.py $(BUILD)/tables

assets/hud.png: tools/gen_hud.py tools/font.py tools/cpcpal.py
	$(PYTHON) tools/gen_hud.py $@

$(BUILD)/hud.rle: assets/hud.png tools/png2scr.py tools/cpcpal.py | $(BUILD)
	$(PYTHON) tools/png2scr.py $< $(BUILD)/hud

$(BUILD)/shield.bin: $(SRC) $(BUILD)/hud.rle $(BUILD)/sprites.inc $(BUILD)/tables.mask \
		$(BUILD)/logo.bin $(BUILD)/font.bin $(BUILD)/sound.inc
	$(RASM) src/main.asm -ob $(BUILD)/shield.bin -s -sa -os $(BUILD)/shield.sym

# The disc: a BASIC loader (SHIELD.BAS) that loads the sprite banks into
# extra RAM, then runs the game (GAME.BIN).
# The loading screen: from the render of assets/loading_scene.blend (Blender,
# Cycles) and the title logo, as a 16-ink Mode 0 picture.
$(BUILD)/loading.bin $(BUILD)/loading.inks &: assets/loading_render.png assets/logo.png tools/mkloading.py tools/cpcpal.py tools/pens.py | $(BUILD)
	$(PYTHON) tools/mkloading.py assets/loading_render.png assets/logo.png $(BUILD)/loading.bin $(BUILD)/loading.inks $(BUILD)/loading.png

$(DSK): $(BUILD)/shield.bin $(BUILD)/sprites.inc $(BUILD)/bank6.bin $(PLANETS:%=$(BUILD)/planet%.bin) $(BUILD)/loading.bin tools/mkdisc.py
	$(PYTHON) tools/mkdisc.py $@ $(BUILD)/shield.bin SCREEN=$(BUILD)/loading.bin BANK4=$(BUILD)/sprites.bank4.bin \
		BANK5=$(BUILD)/sprites.bank5.bin BANK6=$(BUILD)/bank6.bin \
		$(foreach p,$(PLANETS),PLANET$(p)=$(BUILD)/planet$(p).bin)

test: $(DSK) planet-art
	$(PYTHON) tests/test_screen.py
	$(PYTHON) tests/test_player.py
	$(PYTHON) tests/test_generators.py
	$(PYTHON) tests/test_enemies.py
	$(PYTHON) tests/test_game.py
	$(PYTHON) tests/test_planets.py
	$(PYTHON) tests/playtest.py idle gunner keeper
	for p in 2 3 4; do $(PYTHON) tests/playtest.py --planet=$$p keeper || exit 1; done

clean:
	rm -rf $(BUILD)

release: $(DSK)
	mkdir -p release
	cp $(DSK) release/shieldrunner-$(VERSION).dsk
