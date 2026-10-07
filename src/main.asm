; Shieldrunner for the Amstrad CPC 6128, version 1.2.
; Ride the Runner round four planets, shooting what comes and recharging
; the shield generators until the time runs out. See README.md for how it
; plays and how it works; this file has the start-up and the main loop.
;
; Controls (joystick or cursor keys, space = fire, W = whistle): see
; player.asm.

    include "hw.asm"
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
    ld hl,black_pal
    call set_palette
    call sound_init
    call hud_init
    ld a,1
    call load_planet        ; the first planet, from disc (enables interrupts)
    di
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
    call game_keys          ; M, and P: pause (and Esc there: give up)
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
    call next_planet        ; planet clear, and another to go: NZ
    jr nz,main_loop
    call hiscore_check
    jr game_loop

    include "macros.asm"
    include "planet.asm"
    include "system.asm"
    include "scroll.asm"
    include "hud.asm"
    include "sprites.asm"
    include "player.asm"
    include "generators.asm"
    include "enemies.asm"
    include "sound.asm"
    include "logo.asm"
    include "disc.asm"

    align 256
mask_table:
    incbin "../build/tables.mask"
col_fg:                     ; the planet's, per map column (see planet.asm)
    ds 256
    include "../build/sprites.frames"
hud_palette:
    incbin "../build/hud.pal"
logo_data:
    incbin "../build/logo.bin"
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
