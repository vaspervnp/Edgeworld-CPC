; Shieldrunner for the Amstrad CPC 6128.
; Milestone 2: scrolling playfield over a wrap-around planet, with a fixed
; HUD below it (CRTC split), a raster sky and a separate HUD palette.
;
; Controls: left/right (joystick or cursor keys) pick the scroll direction,
; down stops. It scrolls right on its own until told otherwise.

    include "hw.asm"
    include "../build/testplanet.inc"

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
    ld hl,0
    call scroll_init
    call hud_update
    ld a,1
    ld (split_on),a
    ei

main_loop:
    call read_input
    ld a,(joy_state)
    bit 3,a
    jr z,.not_right
    ld a,1
    ld (scroll_dir),a
.not_right:
    ld a,(joy_state)
    bit 2,a
    jr z,.not_left
    ld a,-1
    ld (scroll_dir),a
.not_left:
    ld a,(joy_state)
    bit 1,a
    jr z,.not_down
    xor a
    ld (scroll_dir),a
.not_down:
    ; scroll_pos += scroll_dir (sign extended)
    ld a,(scroll_dir)
    ld e,a
    rla
    sbc a,a
    ld d,a
    ld hl,(scroll_pos)
    add hl,de
    ld (scroll_pos),hl
    call scroll_update_back
    call flip_and_wait
    call swap_buffers
    call hud_update
    jr main_loop

    include "system.asm"
    include "scroll.asm"
    include "hud.asm"

    align 16
tile_data:
    incbin "../build/testplanet.tiles"
map_data:
    incbin "../build/testplanet.map"
pf_palette:
    incbin "../build/testplanet.pal"
hud_palette:
    incbin "../build/hud.pal"
hud_data:
    incbin "../build/hud.scr"
end_of_program:

    assert end_of_program <= #4000
