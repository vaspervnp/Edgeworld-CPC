; Shieldrunner for the Amstrad CPC 6128.
; Milestone 7: the first planet complete: title screen, high scores, the
; countdown, winning and losing, music and sound effects, around the
; player, the shield generators and the enemies on the scrolling planet
; with its fixed HUD, raster sky and sprite engine.
;
; Controls (joystick or cursor keys, space = fire, W = whistle): see
; player.asm.

    include "hw.asm"
    include "../build/testplanet.inc"
    include "../build/sprites.inc"

; The map lives in extra RAM bank 7 (MAP_BANK), paged in at #4000 while
; the scroll and sprite code read it; tools/mkdisc.py loads it there.
map_data equ #4000

LOAD_ADDR equ #0200
STACK_TOP equ #0200

    org LOAD_ADDR
    run LOAD_ADDR

start:
    di
    ld sp,STACK_TOP
    ld bc,GA_PORT*256+RMR_MODE0_NOROM
    out (c),c
    ld bc,#FA7E         ; disc motor off (the firmware is no longer there to do it)
    xor a
    out (c),a
    ; our interrupt handler at #0038
    ld a,#C3
    ld (#0038),a
    ld hl,isr
    ld (#0039),hl
    im 1
    ld hl,black_pal
    call set_palette
    call sound_init
    call hud_init
    ld hl,0
    call scroll_init        ; the CRTC's first setup, before the split runs
    ld a,1
    ld (split_on),a
    ei

game_loop:
    call title_screen
    call game_start
main_loop:
    call read_input
    call player_update      ; also sets scroll_dir
    ; scroll_pos += scroll_dir (sign extended)
    ld a,(scroll_dir)
    ld e,a
    rla
    sbc a,a
    ld d,a
    ld hl,(scroll_pos)
    add hl,de
    ld (scroll_pos),hl
    call gen_update
    call enemies_update
    call list_begin
    call enemy_sprites
    call player_sprites
    call list_end
    call scroll_update_back
    call render_sprites
    call flip_and_wait
    call swap_buffers
    call hud_update
    call game_tick
    jr z,main_loop
    call hiscore_check
    jr game_loop

    include "macros.asm"
    include "system.asm"
    include "scroll.asm"
    include "hud.asm"
    include "sprites.asm"
    include "player.asm"
    include "planet.asm"
    include "generators.asm"
    include "enemies.asm"
    include "sound.asm"
    include "logo.asm"

    align 256
mask_table:
    incbin "../build/tables.mask"
tile_attr:
    incbin "../build/testplanet.attr"
col_fg:
    incbin "../build/testplanet.colfg"
tile_data:                  ; 256-aligned, up to 256 tiles
    incbin "../build/testplanet.tiles"
    align 256
tile_lo:                    ; address of each tile, low bytes then high
t=0
    repeat 256
    db (tile_data+t*16)&#FF
t=t+1
    rend
t=0
    repeat 256
    db (tile_data+t*16)>>8
t=t+1
    rend
    align 256
fg_data:
    incbin "../build/testplanet.fg"
    include "../build/sprites.frames"
pf_palette:
    incbin "../build/testplanet.pal"
hud_palette:
    incbin "../build/hud.pal"
end_of_code:
    assert end_of_code <= #4000

; The HUD page (#4000) uses the first HUD_ROWS*80 bytes of each 2K block;
; the rest of block 0 holds data needed only at start-up, since the 6128's
; extra banks page in over #4000.
; Code and data that never page a bank in and that the interrupt does not
; use go in the spare space of the HUD page's 2K blocks, too.
HUD_PAGE_FREE equ #4000+HUD_ROWS*80
    org HUD_PAGE_FREE
hud_data:
    incbin "../build/hud.rle"
    include "text.asm"
    assert $ <= #4800
    org #4800+HUD_ROWS*80
    include "game.asm"
    assert $ <= #5000
    org #5000+HUD_ROWS*80
    include "title.asm"
    assert $ <= #5800
end_of_program:
