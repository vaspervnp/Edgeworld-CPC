; Planets. Each is a bank image (tools/mkplanet.py, from a description in
; assets/planets/) loaded from disc into extra RAM bank 7 (MAP_BANK) when
; it is played (disc.asm). Paged in at #4000 it holds:

map_data   equ #4000        ; the map: 256 columns of 17 tile numbers
PLANET_HDR equ #5100        ; the parameters below, copied to base RAM
tile_lo    equ #5200        ; tile addresses, low bytes...
tile_hi    equ #5300        ; ...and high bytes
tile_attr  equ #5400        ; per tile: 0, or its foreground overlay + 1
PLANET_COL_FG equ #5500     ; per map column: foreground tiles? (copied to col_fg)
tile_data  equ #5600        ; the tiles, 16 bytes each
fg_data    equ #6600        ; the foreground overlays, 32 bytes each

MAP_COLS   equ 256
MAP_ROWS   equ 17
NUM_PLANETS equ 4
NUM_GENS   equ 4            ; at map columns 32, 96, 160 and 224 on every planet
GEN_ENTRY  equ 5
TITLE_POS  equ 0            ; scroll position the title shows (see logo.asm)

; The current planet's parameters, copied from its header.
planet:
planet_time:  dw 0          ; seconds to hold the shield
shield_fails: db 0          ; drained generators that bring the shield down
spawn_every:  db 0          ; game frames between enemies...
ambient_max:  db 0          ; ...while fewer than this many are about
enemy_mix:    ds 8          ; the spawner picks one of these at random
; Per generator: map column of its left edge (it is 3 columns wide), drain
; per game frame and starting charge, out of 65535. A generator at full
; charge with drain 16 lasts 65535 / 16 / 25 = 164 seconds.
gen_table:    ds NUM_GENS*GEN_ENTRY
pf_palette:   ds 16         ; the playfield's palette (pen 2: generator core)
planet_sky:   ds 3          ; the raster sky's three bands
PLANET_SIZE equ $-planet
