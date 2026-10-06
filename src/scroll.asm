; Hardware scroll engine.
;
; The playfield is 40 CRTC words (80 bytes, 160 Mode 0 pixels) by PLAY_ROWS
; character rows. Each 2K line block of a 16K screen page is a ring of 1024
; words that the CRTC start address (R12/R13) can begin anywhere in, so
; moving the start address by one word scrolls the picture by 4 pixels; only
; the newly exposed column has to be drawn.
;
; A scroll position is a 16-bit count of columns. The CRTC word offset is its
; low 10 bits and the map column its low 8 (the map is 256 columns around),
; so one value addresses both and the planet wraps for free.
;
; Two screen pages (#C000 and #8000) are double buffered. Each buffer
; remembers the position it last showed and catches up column by column to
; the target position before it is displayed again.

SCREEN_WORDS equ 40         ; visible width in CRTC words
SCREEN_BYTES equ SCREEN_WORDS*2

    assert MAP_COLS==256
    assert MAP_ROWS==PLAY_ROWS

; Draw map column (v & 255) at ring word (v & 1023) of one screen page.
; Pages the map's RAM bank in for the while.
; in:  HL = v, A = page high byte (#C0 or #80)
; out: all registers except SP trashed (IY, IXH used)
draw_column:
    ld (.page+1),a
    PAGE MAP_BANK
    ; destination: page + ((v * 2) & #7FF), char row 0, line 0
    push hl
    add hl,hl
    ld a,h
    and 7
.page:
    or 0
    ld d,a
    ld e,l
    pop hl
    ; map pointer: col_ptrs[v & 255] (low bytes, then high bytes 256 on)
    ld h,col_ptrs>>8
    ld a,(hl)
    inc h
    ld h,(hl)
    ld l,a
    push hl
    pop iy
    ld a,(.page+1)
    ld (.rowpage+1),a
    ld ixh,MAP_ROWS
.row:
    ld a,(iy+0)
    inc iy
    TILE_SRC
    ; 8 lines of 2 bytes, each line #800 further down. DE is even, so the
    ; first LDI never carries into D; the second byte is stored by hand
    ; because DE+1 can cross a 256-byte boundary. Tiles are 16-byte aligned,
    ; so INC L is enough for the source.
    repeat 7
    ldi
    ld a,(hl)
    ld (de),a
    inc l
    dec e
    ld a,d
    add 8
    ld d,a
    rend
    ldi
    ld a,(hl)
    ld (de),a
    ; next char row: 80 bytes on from the row's start (E is one past it),
    ; carrying into the ring block and wrapping it inside the 2K ring
    ld a,e
    add a,SCREEN_BYTES-1
    ld e,a
    ld a,d
    adc a,0
    and 7
.rowpage:
    or 0
    ld d,a
    dec ixh
    jr nz,.row
    PAGE RAM_BASE
    ret

; Fill both screen pages for scroll position HL and show the front one
; (the game must not be flipping buffers meanwhile).
scroll_init:
    ld (scroll_pos),hl
    ld (front_pos),hl
    ld (back_pos),hl
    ld a,#C0
    ld (front_page),a
    ld a,#30
    ld (front_r12),a
    ld a,#80
    ld (back_page),a
    ld a,#20
    ld (back_r12),a
    ld hl,list_a
    ld (front_list),hl
    ld hl,list_b
    ld (back_list),hl
    ld hl,layouts_a
    ld (front_layouts),hl
    ld hl,layouts_b
    ld (back_layouts),hl
    xor a                   ; no sprites shown in either buffer
    ld (list_a),a
    ld (list_b),a
    ld (layouts_a),a
    ld (layouts_b),a
    ld a,(front_page)
    call fill_page
    ld a,(back_page)
    call fill_page
    ; show the front page now
    ld hl,(front_pos)
    ld a,(front_r12)
    call crtc_addr
    ld (pf_crtc),de
    ld a,(split_on)         ; once the split runs, the interrupts set the CRTC
    or a
    ret nz
    jp crtc_init

; Draw all 40 visible columns of position (scroll_pos) into page A.
fill_page:
    ld (.pg+1),a
    ld hl,(scroll_pos)
    ld b,SCREEN_WORDS
.col:
    push bc
    push hl
.pg:
    ld a,0
    call draw_column
    pop hl
    pop bc
    inc hl
    djnz .col
    ret

; R12/R13 for position HL on a page whose R12 page bits are A.
; out: D = R12, E = R13
crtc_addr:
    ld e,l
    ld d,a
    ld a,h
    and 3
    or d
    ld d,a
    ret

; Bring the back buffer to scroll_pos and queue its CRTC address for the flip.
scroll_update_back:
.loop:
    ld hl,(scroll_pos)
    ld de,(back_pos)
    or a
    sbc hl,de
    jr z,.done
    bit 7,h
    jr nz,.left
    ; scrolled right: the new column is the last visible one
    inc de
    ld (back_pos),de
    ld hl,SCREEN_WORDS-1
    add hl,de
    ld a,(back_page)
    call draw_column
    jr .loop
.left:
    ; scrolled left: the new column is the first visible one
    dec de
    ld (back_pos),de
    ex de,hl
    ld a,(back_page)
    call draw_column
    jr .loop
.done:
    ld hl,(back_pos)
    ld a,(back_r12)
    call crtc_addr
    ld (next_crtc),de
    ret

; After a flip the shown buffer becomes the back one.
swap_buffers:
    ld hl,front_pos
    ld de,back_pos
    ld b,BUF_STATE
.swap:
    ld c,(hl)
    ld a,(de)
    ld (hl),a
    ld a,c
    ld (de),a
    inc hl
    inc de
    djnz .swap
    ret

; Start of each map column: low bytes, then high bytes.
    align 256
col_ptrs:
col=0
    repeat 256
    db (map_data+col*MAP_ROWS)&#FF
col=col+1
    rend
col=0
    repeat 256
    db (map_data+col*MAP_ROWS)>>8
col=col+1
    rend

scroll_pos: dw 0            ; position to show next
scroll_dir: db 0            ; columns per displayed frame: -1, 0 or 1

; Buffer state: position shown, page high byte, R12 page bits, sprite list
; and sprite layouts (BUF_STATE bytes each, same layout, swapped by
; swap_buffers).
BUF_STATE equ 8
front_pos:  dw 0
front_page: db 0
front_r12:  db 0
front_list: dw 0
front_layouts: dw 0
back_pos:   dw 0
back_page:  db 0
back_r12:   db 0
back_list:  dw 0
back_layouts: dw 0
