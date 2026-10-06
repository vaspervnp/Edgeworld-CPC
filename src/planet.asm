; Data for the current planet (the test planet). Must match the art in
; tools/gen_testplanet.py and tools/gen_hud.py (GENERATOR_COLS).

NUM_GENS equ 4

; Per generator: map column of its left edge (it is 3 columns wide), drain
; per game frame and starting charge, out of 65535. A generator at full
; charge with drain 16 lasts 65535 / 16 / 25 = 164 seconds. Left alone,
; these drain at 123, 82, 71 and 82 seconds: the shield fails at 82.
gen_table:
    db 32 : dw 20, #F000
    db 96 : dw 22, #B000
    db 160 : dw 30, #D000
    db 224 : dw 18, #9000
GEN_ENTRY equ 5

; Enemy pressure: the spawner brings one in every SPAWN_EVERY game frames
; while fewer than AMBIENT_MAX are about (breach waves and the carrier
; come on top).
SPAWN_EVERY equ 75
AMBIENT_MAX equ 3

; Enemy mix: the spawner picks one of these 8 at random.
enemy_mix:
    db E_DRIFTER, E_DRIFTER, E_TRACKER, E_CRAWLER
    db E_CRAWLER, E_THROWER, E_DRIFTER, E_TRACKER

PLANET_TIME equ 180         ; seconds to hold the shield
SHIELD_FAILS equ 3          ; drained generators that bring the shield down
TITLE_POS   equ 0           ; scroll position the title shows (see logo.asm)
