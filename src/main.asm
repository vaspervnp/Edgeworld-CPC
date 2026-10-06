; Shieldrunner for the Amstrad CPC 6128.
; Milestone 4: the player (riding, jumping, shooting, dismounting,
; whistling) on the scrolling planet with its fixed HUD, raster sky and
; sprite engine, with 8 drifters as the enemy load test.
;
; Controls (joystick or cursor keys, space = fire, W = whistle): see
; player.asm.

    include "hw.asm"
    include "../build/testplanet.inc"
    include "../build/sprites.inc"

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
    ld hl,pf_palette
    call set_palette
    call hud_init
    call player_init
    call hud_spares
    ld hl,0
    call scroll_init
    call hud_update
    ld a,1
    ld (split_on),a
    ei

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
    call list_begin
    call demo_update
    call player_sprites
    call list_end
    call scroll_update_back
    call render_sprites
    call flip_and_wait
    call swap_buffers
    call hud_update
    jr main_loop

    include "macros.asm"
    include "system.asm"
    include "scroll.asm"
    include "hud.asm"
    include "sprites.asm"
    include "player.asm"
    include "demo.asm"

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
map_data:
    incbin "../build/testplanet.map"
pf_palette:
    incbin "../build/testplanet.pal"
hud_palette:
    incbin "../build/hud.pal"
end_of_code:
    assert end_of_code <= #4000

; The HUD page (#4000) uses the first HUD_ROWS*80 bytes of each 2K block;
; the rest of block 0 holds data the engine itself never reads (start-up
; and demo data), since the 6128's extra banks will page in over #4000.
HUD_PAGE_FREE equ #4000+HUD_ROWS*80
    org HUD_PAGE_FREE
    align 256
demo_x:
    incbin "../build/tables.demo",0,256
demo_y:
    incbin "../build/tables.demo",256,256
hud_data:
    incbin "../build/hud.rle"
end_of_program:
    assert end_of_program <= #4800
