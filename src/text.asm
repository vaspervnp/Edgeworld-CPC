; Text in the HUD page: the 3x5 font of tools/font.py, 4 pixels (2 bytes)
; a character, drawn opaque in one pen on pen 0.
;
; Runs with base RAM paged in (it lives in the HUD page's spare space).

; HL = HUD address of line A (0-63), byte C. Trashes A.
hud_addr:
    push de
    ld e,a
    and 7
    add a,a
    add a,a
    add a,a
    add a,HUD_BASE>>8
    ld h,a
    ld l,c
    ld a,e
    rrca
    rrca
    and #0E                 ; character row * 2
    ld e,a
    ld d,0
    push hl
    ld hl,row80
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    pop hl
    add hl,de
    pop de
    ret

row80: dw 0, 80, 160, 240, 320, 400, 480, 560

; Draw the 0-terminated string DE at address HL in pen A.
; Out: DE just past the terminator. Trashes A, BC, HL.
draw_text:
    call set_pen
.char:
    ld a,(de)
    inc de
    or a
    ret z
    push de
    push hl
    call draw_char
    pop hl
    inc hl
    inc hl
    pop de
    jr .char

; The pen's pixel bytes go into draw_char's code. Trashes A.
set_pen:
    push hl
    push bc
    ld hl,pen_left
    ld c,a
    ld b,0
    add hl,bc
    ld a,(hl)
    ld (dc_l1+1),a
    ld (dc_l2+1),a
    srl a                   ; the right pixel's bits are one lower
    ld (dc_r1+1),a
    pop bc
    pop hl
    ret

; Character A at HL. Trashes A, BC, DE, HL.
draw_char:
    sub 32
    cp 64
    jr c,dc_known
    xor a
dc_known:
    ld e,a
    ld d,0
    push hl
    ld h,d
    ld l,e
    add hl,hl
    add hl,hl
    add hl,de
    ld de,font_data
    add hl,de
    ex de,hl
    pop hl
    ld b,5
dc_row:
    ld a,(de)               ; the row's 3 pixels in bits 7-5
    inc de
    ld c,a
    xor a
    rl c
    jr nc,dc_p1
dc_l1:
    or 0
dc_p1:
    rl c
    jr nc,dc_p2
dc_r1:
    or 0
dc_p2:
    ld (hl),a
    inc hl
    xor a
    rl c
    jr nc,dc_p3
dc_l2:
    or 0
dc_p3:
    ld (hl),a
    dec hl
    ld a,h                  ; next line
    add a,8
    ld h,a
    and #38
    jr nz,dc_same
    ld a,l
    add a,80
    ld l,a
    ld a,h
    adc a,#C0
    ld h,a
dc_same:
    djnz dc_row
    ret

; Draw string DE centred on HUD line A in pen C.
; Out: DE just past the terminator. Trashes A, BC, HL.
draw_centred:
    push af
    push de
    ld b,0
.len:
    ld a,(de)
    or a
    jr z,.counted
    inc de
    inc b
    jr .len
.counted:
    pop de
    ld a,40
    sub b
    ld b,a
    pop af
    push bc
    ld c,b
    call hud_addr
    pop bc
    ld a,c
    jp draw_text

; Draw a list of centred lines from HL: line, pen, 0-terminated string;
; #FF ends the list. Trashes A, BC, DE, HL.
text_lines:
    ld a,(hl)
    cp #FF
    ret z
    inc hl
    ld b,a
    ld c,(hl)
    inc hl
    ex de,hl
    ld a,b
    call draw_centred
    ex de,hl
    jr text_lines

; Clear B whole HUD lines from line A. Trashes A, BC, DE, HL.
hud_clear:
    push af
    push bc
    ld c,0
    call hud_addr
    ld (hl),0
    ld d,h
    ld e,l
    inc de
    ld bc,79
    ldir
    pop bc
    pop af
    inc a
    djnz hud_clear
    ret

; num_buf = HL as 5 decimal digits, 0-terminated. Trashes A, BC, DE, HL.
num_to_text:
    ld de,num_buf
    ld bc,-10000
    call .digit
    ld bc,-1000
    call .digit
    ld bc,-100
    call .digit
    ld bc,-10
    call .digit
    ld a,l
    add a,'0'
    ld (de),a
    inc de
    xor a
    ld (de),a
    ret
.digit:
    ld a,'0'-1
.count:
    inc a
    add hl,bc
    jr c,.count
    sbc hl,bc               ; one too many (carry is clear)
    ld (de),a
    inc de
    ret

; Pen p's left-pixel byte in Mode 0: bits 0-3 of p in bits 7, 3, 5, 1.
pen_left:
p=0
    repeat 16
    db ((p&1)<<7)|((p&2)<<2)|((p&4)<<3)|((p&8)>>2)
p=p+1
    rend

font_data:
    incbin "../build/font.bin"

num_buf: ds 8
