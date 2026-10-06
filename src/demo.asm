; Load test: 8 drifters swooping around the view on looping paths that take
; them past both edges and behind the foreground spires, the most enemies
; the game is meant to show at once. They stand in for the enemies of
; milestone 6 and do nothing yet.

NUM_DRIFTERS  equ 8
DRIFTER_X_BIAS equ 12       ; demo_x holds screen x + 12

; Append the drifters to the sprite list (IX, from list_begin).
demo_update:
    ld hl,demo_t
    inc (hl)
    ld hl,(scroll_pos)
    add hl,hl
    add hl,hl
    ld de,-DRIFTER_X_BIAS
    add hl,de
    ld (.vx+1),hl
    ; frames alternate every 4 ticks, out of step with the neighbours
    ld a,(demo_t)
    rrca
    rrca
    and 1
    ld c,a
    ld hl,demo_phase
    ld b,NUM_DRIFTERS
.drifter:
    ld a,c
    xor 1
    ld c,a
    add a,SPR_DRIFTER0
    ld (ix+0),a
    ; x = view + demo_x[x phase] - bias, x phase += 1
    inc (hl)
    ld e,(hl)
    inc hl
    ld d,demo_x>>8
    ld a,(de)
    push hl
.vx:
    ld hl,0
    add a,l
    ld l,a
    adc a,h
    sub l
    and 3
    ld (ix+2),a
    ld (ix+1),l
    pop hl
    ; y = demo_y[y phase], y phase += 2
    ld a,(hl)
    add a,2
    ld (hl),a
    inc hl
    ld e,a
    ld d,demo_y>>8
    ld a,(de)
    ld (ix+3),a
    ld de,REC_SIZE
    add ix,de
    djnz .drifter
    ld hl,list_count
    ld a,(hl)
    add a,NUM_DRIFTERS
    ld (hl),a
    ret

demo_t:    db 0
; x and y path phase of each drifter
demo_phase:
n=0
    repeat NUM_DRIFTERS
    db (n*32)&255,(n*45)&255
n=n+1
    rend
