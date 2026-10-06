; Macros shared by the engine.

; Gate array RAM configuration cfg: base RAM, or an extra bank at #4000.
; Trashes BC.
macro PAGE cfg
    ld bc,GA_PORT*256+{cfg}
    out (c),c
mend

; HL = tile_data + A * 16, from the 256-aligned tables tile_lo / tile_hi.
macro TILE_SRC
    ld l,a
    ld h,tile_lo>>8
    ld a,(hl)
    inc h
    ld h,(hl)
    ld l,a
mend

; BC = ring address of the next character row: C + 80, carrying into the
; ring block (low 3 bits of B) and wrapping it, page bits kept. Trashes A, E.
macro NEXT_ROW
    ld a,c
    add a,SCREEN_WORDS*2
    ld c,a
    ld a,b
    adc a,0
    and 7
    ld e,a
    ld a,b
    and #F8
    or e
    ld b,a
mend

; HL = the foreground overlay of tile A, or jump to skip if it has none.
; Overlays are 32 bytes, fg_data is 256-aligned.
macro OVL_SRC skip
    ld l,a
    ld h,tile_attr>>8
    ld a,(hl)
    or a
    jr z,{skip}
    dec a
    rrca
    rrca
    rrca
    ld l,a
    and #1F
    add a,fg_data>>8
    ld h,a
    ld a,l
    and #E0
    ld l,a
mend
