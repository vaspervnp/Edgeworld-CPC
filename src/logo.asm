; The title logo (tools/gen_logo.py), kept in the last sprite bank after the
; sprites, drawn through its pen 0 mask over the title's playfield. It reads
; from an extra bank, so it stays below #4000.

LOGO_BANK equ #C6
LOGO_ADDR equ #4000+#2800
LOGO_W    equ 72            ; bytes a line
LOGO_H    equ 32
LOGO_LINE equ 4             ; where it goes on the title screen
LOGO_BYTE equ 4

; Draw the logo into page #C000, shown at scroll position 0 (TITLE_POS),
; where the screen is laid out plainly: line y at (y & 7) * #800 + (y >> 3) * 80.
draw_logo:
    PAGE LOGO_BANK
    ld hl,LOGO_ADDR
    ld de,#C000+(LOGO_LINE&7)*#800+(LOGO_LINE>>3)*80+LOGO_BYTE
    ld c,LOGO_H
.line:
    push de
    ld b,LOGO_W
.byte:
    ld a,(hl)
    inc hl
    or a
    jr z,.clear
    push hl
    ld l,a
    ld h,mask_table>>8
    ld a,(de)
    and (hl)
    or l
    ld (de),a
    pop hl
.clear:
    inc de
    djnz .byte
    pop de
    ld a,d
    add a,8
    ld d,a
    and #38
    jr nz,.same
    ld a,e
    add a,80
    ld e,a
    ld a,d
    adc a,#C0
    ld d,a
.same:
    dec c
    jr nz,.line
    PAGE RAM_BASE
    ret
