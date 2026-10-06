; The HUD: a fixed 8-row strip in screen page #4000, shown below the
; playfield by the CRTC split (see system.asm). It never scrolls and is not
; double buffered.
;
; Base RAM bank 1 (#4000-#7FFF) is where the 6128's extra banks page in,
; but the CRTC always reads base RAM, so the HUD stays on screen while a
; bank is mapped there; only writing to it needs base RAM paged in.

HUD_BASE  equ #4000

; Radar layout, matching tools/gen_hud.py: the interior starts at byte 8
; (pixel 16) and is 64 bytes wide, one byte per 4 map columns.
RADAR_X0_BYTE   equ 8
MARKER_LINE     equ 24      ; HUD lines 24-26
MARKER_ADDR     equ HUD_BASE+(MARKER_LINE&7)*#800+(MARKER_LINE>>3)*80
MARKER_BYTE     equ #30     ; pen 4 (white), both pixels
RADAR_BG_BYTE   equ #C0     ; pen 1 (radar background), both pixels
VIEW_CENTRE     equ 20      ; columns from the left edge to the view centre

; Unpack the HUD picture into its screen page: 8 run-length encoded
; pixel-line blocks (see tools/png2scr.py).
hud_init:
    ld hl,hud_data
    ld de,HUD_BASE
.block:
    push de
    call rle_unpack
    pop de
    ld a,d
    add 8
    ld d,a
    cp #80
    jr c,.block
    ret

; Unpack from HL to DE up to the end marker; HL ends just after it.
rle_unpack:
    ld a,(hl)
    inc hl
    or a
    ret z
    bit 7,a
    jr nz,.run
    ld c,a
    ld b,0
    ldir
    jr rle_unpack
.run:
    and #7F
    ld b,a
    ld a,(hl)
    inc hl
.fill:
    ld (de),a
    inc de
    djnz .fill
    jr rle_unpack

; Move the radar's view marker to the current scroll position.
hud_update:
    ld hl,(marker_ptr)
    ld a,RADAR_BG_BYTE
    call .draw
    ld a,(scroll_pos)
    add VIEW_CENTRE
    rrca
    rrca
    and 63
    ld e,a
    ld d,0
    ld hl,MARKER_ADDR+RADAR_X0_BYTE
    add hl,de
    ld (marker_ptr),hl
    ld a,MARKER_BYTE
.draw:                  ; byte A on 3 lines from HL
    ld c,a
    ld (hl),c
    ld a,h
    add 8
    ld h,a
    ld (hl),c
    add 8
    ld h,a
    ld (hl),c
    ret

marker_ptr: dw MARKER_ADDR+RADAR_X0_BYTE
