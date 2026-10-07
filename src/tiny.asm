; Tiny sprites: the rider's bolts, bombs and rocks. Small, quick and often
; several at once, they would cost as much as a big sprite each through the
; sprite engine (a record, a layout, a cell restore). Instead they are
; drawn last, over everything (the foreground too), at even x, straight
; from (mask, pixels) pairs in base RAM (tiny_frames, tools/spritec.py),
; and the bytes they cover are saved with their addresses; before that
; buffer is drawn again, the saved bytes go back, last first, so tiny ones
; that overlapped come off in order. Then the sprite restore runs as usual.
;
; list_add sends frames from SPR_TINY on to tiny_add. Each screen buffer has
; a block (back_tiny): the records drawn (count, then frame, x, y; for the
; tests), then the saved bytes (count, then address and byte each).
;
; Lives in the HUD page: it never pages a bank.

TINY_MAX   equ 8            ; 4 bolts and 4 missiles
TINY_RECS  equ 1+TINY_MAX*4
TINY_BYTES equ 64           ; bytes saved, at most: 4 * 4 (bolts) + 4 * 8
TINY_BLOCK equ TINY_RECS+1+TINY_BYTES*3

; Add tiny frame A at world x HL (pixels), y C to this frame's list.
; Trashes A, DE, HL (as list_add).
tiny_add:
    ex de,hl
    ld hl,tiny_new
    push af
    ld a,(hl)
    cp TINY_MAX
    jr nc,.full
    inc (hl)
    add a,a
    add a,a
    inc a
    add a,l
    ld l,a
    adc a,h
    sub l
    ld h,a
    pop af
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld (hl),c
    ret
.full:
    pop af
    ret

; Put back what the back buffer's tiny sprites covered, last first.
tiny_undo:
    ld hl,(back_tiny)
    ld de,TINY_RECS
    add hl,de
    ld a,(hl)
    or a
    ret z
    ld (hl),0
    ld b,a
    ld e,a
    ld d,0
    add hl,de
    add hl,de
    add hl,de               ; the last byte saved
.undo:
    ld a,(hl)
    dec hl
    ld d,(hl)
    dec hl
    ld e,(hl)
    dec hl
    ld (de),a
    djnz .undo
    ret

; Draw this frame's tiny sprites into the back buffer, saving what they
; cover. The sprites must have been drawn.
tiny_draw:
    ld de,(back_tiny)
    ld hl,tiny_new
    ld bc,TINY_RECS
    ldir                    ; the records, for the tests
    inc de
    push de
    pop iy                  ; saved bytes go here
    ld a,(tiny_new)
    or a
    jr z,.done
    ld b,a
    ld ix,tiny_new+1
.rec:
    push bc
    call tiny_one
    pop bc
    ld de,4
    add ix,de
    djnz .rec
.done:
    ; count = (IY - start) / 3
    push iy
    pop hl
    ld de,(back_tiny)
    or a
    sbc hl,de
    ld de,-(TINY_RECS+1)
    add hl,de
    ld a,l
    ld c,0
.third:
    sub 3
    jr c,.counted
    inc c
    jr .third
.counted:
    ld hl,(back_tiny)
    ld de,TINY_RECS
    add hl,de
    ld (hl),c
    ret

; Draw the tiny sprite whose record is at IX; IY = where to save.
tiny_one:
    ; its frame: W bytes, height, data
    ld a,(ix+0)
    sub SPR_TINY
    add a,a
    add a,a
    add a,tiny_frames&#FF
    ld l,a
    adc a,tiny_frames>>8
    sub l
    ld h,a
    ld a,(hl)
    ld (to_w+1),a
    inc hl
    ld a,(hl)
    ld (to_h+1),a
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    push de                 ; the data
    ; screen byte column = (world x - view x) / 2, signed (-256..255)
    ld hl,(back_pos)
    add hl,hl
    add hl,hl
    ex de,hl
    ld l,(ix+1)
    ld h,(ix+2)
    or a
    sbc hl,de
    ld a,h
    and 3
    bit 1,a
    jr z,.signed
    or #FC
.signed:
    ld h,a
    sra h
    rr l                    ; even x: the odd pixel dropped
    ; on screen at all? -W < column < VIEW_BYTES
    ld a,h
    or a
    jr z,.right
    inc a
    jr nz,.off              ; far either way
    ld a,(to_w+1)
    add a,l
    jr nc,.off
    jr z,.off               ; ends just left of the view
    jr .on
.right:
    ld a,l
    cp VIEW_BYTES
    jr c,.on
.off:
    pop de
    ret
.on:
    ld a,l
    ld (to_col+1),a
    ; first line: ring offset of row y/8, plus the view and the column
    push hl
    ld a,(ix+3)
    rrca
    rrca
    rrca
    and 31
    add a,a
    add a,row_off&#FF
    ld l,a
    adc a,row_off>>8
    sub l
    ld h,a
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(back_pos)
    add hl,hl
    add hl,de
    pop de
    add hl,de
    ld a,(ix+3)
    and 7
    add a,a
    add a,a
    add a,a
    ld c,a
    ld a,h
    and 7
    or c
    ld c,a
    ld a,(back_page)
    or c
    ld h,a                  ; HL = its screen address
    pop de                  ; DE = its data
to_h:
    ld b,0
to_line:
    push bc
    push hl
to_col:
    ld c,0                  ; the byte's column in the view
to_w:
    ld b,0
.byte:
    ld a,c
    cp VIEW_BYTES
    jr nc,.skip             ; outside the view (left of it is 128 up)
    ld (iy+0),l             ; save it
    ld (iy+1),h
    ld a,(hl)
    ld (iy+2),a
    inc iy
    inc iy
    inc iy
    ld a,(de)               ; mask...
    and (hl)
    inc de
    ex de,hl
    or (hl)                 ; ...and pixels
    ex de,hl
    ld (hl),a
    inc de
    jr .moved
.skip:
    inc de
    inc de
.moved:
    inc c
    inc l                   ; the next byte, round the 2K ring
    jr nz,.same
    ld a,h
    inc a
    xor h
    and 7
    xor h
    ld h,a
.same:
    djnz .byte
    pop hl
    ; the next line: 8 lines in a character row, then the next row
    ld a,h
    add a,8
    ld h,a
    and #38
    jr nz,.next
    ld a,h
    sub #40
    ld h,a
    ld a,l
    add a,VIEW_BYTES
    ld l,a
    jr nc,.next
    ld a,h
    inc a
    xor h
    and 7
    xor h
    ld h,a
.next:
    pop bc
    djnz to_line
    ret

    include "../build/sprites.tiny"

tiny_new:   ds TINY_RECS    ; this frame's
tiny_a:     ds TINY_BLOCK   ; the two buffers' blocks
tiny_b:     ds TINY_BLOCK
