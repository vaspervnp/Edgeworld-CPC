; Shield generators: charge, drain, state, breaches, and how they show: the
; core of the generator in view (pen 2 of the playfield palette, used by
; nothing else; generators are 64 columns apart, so only one fits in the
; 40-column view), the radar dots and the SHIELD gauge in the HUD.
;
; Each generator drains every game frame at its own rate. Below
; GEN_UNSTABLE it is unstable (core and radar dot flash); at 0 it is drained
; and lets a breach in: breaches counts them and breach_new has a bit per
; generator for the enemy code to take (milestone 6). The player recharges
; a generator on foot (see update_charging in player.asm): it does not
; drain meanwhile, and a drained one can be brought back.

GEN_UNSTABLE  equ #6000     ; below this, unstable
GS_STABLE     equ 0
GS_UNSTABLE   equ 1
GS_DRAINED    equ 2

CORE_PEN      equ 2
CORE_STABLE   equ #52       ; bright green
CORE_FLASH1   equ #4A       ; bright yellow
CORE_FLASH2   equ #4E       ; orange
CORE_DRAINED  equ #5C       ; red
CORE_PULSE    equ #4B       ; bright white: pump now
CORE_STALL    equ #4C       ; bright red: pumped at the wrong time

; HUD (see tools/gen_hud.py): radar dots on lines 18-21, one byte each;
; the gauge on lines 49-53, bytes 52-75.
DOT_LINE      equ 18
DOT_BYTE0     equ 8         ; byte of the radar's first column; + (col+1)/4
DOT_STABLE    equ #F0       ; pen 5, bright green
DOT_UNSTABLE  equ #3C       ; pen 6, bright yellow
DOT_DRAINED   equ #FC       ; pen 7, bright red
DOT_OFF       equ #C0       ; pen 1, the radar's background
GAUGE_LINE    equ 49
GAUGE_BYTE    equ 52
GAUGE_BYTES   equ 24
GAUGE_EMPTY   equ #C0

; Charge and state from the planet's table; draw the HUD parts.
gen_init:
    ld ix,gen_table
    ld hl,gen_charge
    ld b,NUM_GENS
.gen:
    ld a,(ix+3)
    ld (hl),a
    inc hl
    ld a,(ix+4)
    ld (hl),a
    inc hl
    ld de,GEN_ENTRY
    add ix,de
    djnz .gen
    xor a
    ld (breaches),a
    ld (breach_new),a
    ld a,#FF
    ld hl,dot_shown
    ld b,NUM_GENS
.forget:
    ld (hl),a
    inc hl
    djnz .forget
    ld (gauge_shown),a
    jp gen_update.states

; One game frame: drain, states, breaches, the core colour, the HUD.
gen_update:
    ld hl,gen_tick
    inc (hl)
    ld ix,gen_table
    ld hl,gen_charge
    ld c,0                  ; generator number
.drain:
    ; the one being recharged does not drain
    ld a,(pl_mode)
    cp MODE_CHARGING
    jr nz,.draining
    ld a,(pl_gen)
    cp c
    jr z,.next
.draining:
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    or e
    jr z,.empty             ; already drained
    ex de,hl
    push bc
    ld c,(ix+1)
    ld b,(ix+2)
    or a
    sbc hl,bc
    pop bc
    jr nc,.store
    ld hl,0
.store:
    ex de,hl
    ld (hl),d
    dec hl
    ld (hl),e
    ld a,d
    or e
    jr nz,.next
    ; just drained: a breach
    push hl
    ld hl,breaches
    inc (hl)
    ld a,c
    call gen_bit
    ld hl,breach_new
    or (hl)
    ld (hl),a
    ld a,SFX_ALARM
    call sfx_play
    pop hl
    jr .next
.empty:
    dec hl
.next:
    inc hl
    inc hl
    ld de,GEN_ENTRY
    add ix,de
    inc c
    ld a,c
    cp NUM_GENS
    jr c,.drain
.states:
    ld hl,gen_charge
    ld de,gen_state
    ld b,NUM_GENS
.state:
    ld a,(hl)
    inc hl
    ld c,(hl)
    inc hl
    or c
    ld a,GS_DRAINED
    jr z,.set
    ld a,c
    cp GEN_UNSTABLE>>8
    ld a,GS_UNSTABLE
    jr c,.set
    xor a                   ; GS_STABLE
.set:
    ld (de),a
    inc de
    djnz .state
    call nearest_gen
    call core_colour
    call radar_dots
    jp shield_gauge

; A = the bit of generator A.
gen_bit:
    ld b,a
    inc b
    xor a
    scf
.shift:
    rla
    djnz .shift
    ret

; near_gen = the generator nearest the middle of the view.
nearest_gen:
    ld a,(scroll_pos)
    add a,SCREEN_WORDS/2
    ld c,a                  ; middle column
    ld ix,gen_table
    ld b,0                  ; generator number
    ld e,255                ; best distance
.gen:
    ld a,(ix+0)
    inc a                   ; its middle column
    sub c
    jp p,.positive
    neg
.positive:
    cp e
    jr nc,.further
    ld e,a
    ld a,b
    ld (near_gen),a
.further:
    push de
    ld de,GEN_ENTRY
    add ix,de
    pop de
    inc b
    ld a,b
    cp NUM_GENS
    jr c,.gen
    ret

; Pen 2: the state of the generator in view, or the pump pulse while the
; player recharges it.
core_colour:
    ld a,(near_gen)
    ld c,a
    ld a,(pl_mode)
    cp MODE_CHARGING
    jr nz,.state
    ld a,(pl_gen)
    cp c
    jr nz,.state
    ld a,(pl_stall)
    or a
    ld a,CORE_STALL
    jr nz,.set
    ld a,(pl_pulse)
    cp PULSE_WINDOW
    ld a,CORE_PULSE
    jr nc,.set
.state:
    ld b,0
    ld hl,gen_state
    add hl,bc
    ld a,(hl)
    cp GS_UNSTABLE
    ld a,CORE_STABLE
    jr c,.set
    ld a,CORE_DRAINED
    jr nz,.set
    ld a,(gen_tick)
    and 4
    ld a,CORE_FLASH1
    jr z,.set
    ld a,CORE_FLASH2
.set:
    ld (pf_palette+CORE_PEN),a
    ret

; Redraw the radar dots that changed: steady green, flashing yellow,
; steady red.
radar_dots:
    ld ix,gen_table
    ld hl,gen_state
    ld de,dot_shown
    ld b,NUM_GENS
.dot:
    ld a,(hl)
    cp GS_UNSTABLE
    ld c,DOT_STABLE
    jr c,.colour
    ld c,DOT_DRAINED
    jr nz,.colour
    ld c,DOT_UNSTABLE
    ld a,(gen_tick)
    and 8
    jr z,.colour
    ld c,DOT_OFF
.colour:
    ld a,(de)
    cp c
    jr z,.same
    ld a,c
    ld (de),a
    push hl
    push de
    ; its column on the radar: 2 pixels per 4 map columns
    ld a,(ix+0)
    inc a
    rrca
    rrca
    and 63
    add a,DOT_BYTE0
    ld e,a
    ld d,0
    ld hl,HUD_BASE+(DOT_LINE&7)*#800+(DOT_LINE>>3)*80
    add hl,de
    ld de,#800
    repeat 4
    ld (hl),c
    add hl,de
    rend
    pop de
    pop hl
.same:
    inc hl
    inc de
    push de
    ld de,GEN_ENTRY
    add ix,de
    pop de
    djnz .dot
    ret

; Redraw the SHIELD gauge if it changed: the charge of the generator in
; view, 24 bytes for full, in its state's colour.
shield_gauge:
    ld a,(end_timer)        ; the end message is over the HUD's text rows
    or a
    ret nz
    ld a,(near_gen)
    ld c,a
    ld b,0
    ld hl,gen_state
    add hl,bc
    ld a,(hl)
    or a
    ld e,DOT_STABLE
    jr z,.colour
    ld e,DOT_UNSTABLE
.colour:
    ld hl,gen_charge+1
    add hl,bc
    add hl,bc
    ld a,(hl)               ; charge / 256
    ld l,a
    ld h,0
    ld c,l
    ld b,h
    add hl,hl
    add hl,bc               ; * 3
    ld bc,31
    add hl,bc
    add hl,hl
    add hl,hl
    add hl,hl
    ld a,h                  ; (charge / 256 * 3 + 31) / 32: 0-24 bytes
    ; what is shown: bytes, and the colour in the top bits
    ld d,a
    ld a,e
    and #C0
    or d
    ld hl,gauge_shown
    cp (hl)
    ret z
    ld (hl),a
    ld hl,gauge_lines
    ld c,GAUGE_BYTES

; Draw a 5-line HUD bar: on each line at the addresses at HL, D bytes of
; colour E, then up to C bytes of the empty colour.
draw_bar:
    ld b,5
.line:
    push bc
    push hl
    ld a,(hl)
    inc hl
    ld h,(hl)
    ld l,a
    ld a,d
    or a
    jr z,.empty
    ld b,d
.fill:
    ld (hl),e
    inc l
    djnz .fill
.empty:
    ld a,c
    sub d
    jr z,.done
    ld b,a
.rest:
    ld (hl),GAUGE_EMPTY
    inc l
    djnz .rest
.done:
    pop hl
    inc hl
    inc hl
    pop bc
    djnz .line
    ret

gauge_lines:
y=GAUGE_LINE
    repeat 5
    dw HUD_BASE+(y&7)*#800+(y>>3)*80+GAUGE_BYTE
    assert ((HUD_BASE+(y&7)*#800+(y>>3)*80+GAUGE_BYTE)&#FF)+GAUGE_BYTES <= 256
y=y+1
    rend

; Add DE to the charge of the generator being recharged, up to full.
charge_gen:
    ld a,(pl_gen)
    add a,a
    ld c,a
    ld b,0
    ld hl,gen_charge
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    add hl,bc
    jr nc,.store
    ld hl,#FFFF
.store:
    ex de,hl
    ld (hl),d
    dec hl
    ld (hl),e
    ret

; Carry clear and A = the generator the rider on foot stands at, if any.
gen_at_rider:
    ld hl,(pl_x)
    TO_PIXELS
    ld de,4                 ; the rider's middle
    add hl,de
    ld (.rider+1),hl
    ld ix,gen_table
    ld b,0
.gen:
    ld l,(ix+0)
    ld h,0
    add hl,hl
    add hl,hl
    ld de,6
    add hl,de               ; the generator's middle, pixels
    ex de,hl
.rider:
    ld hl,0
    or a
    sbc hl,de
    ld de,GEN_REACH
    add hl,de               ; within reach: 0 to 2 * GEN_REACH (round the planet)
    ld a,h
    and 3
    jr nz,.far
    ld a,l
    cp GEN_REACH*2+1
    jr nc,.far
    ld a,b
    or a                    ; carry clear
    ret
.far:
    ld de,GEN_ENTRY
    add ix,de
    inc b
    ld a,b
    cp NUM_GENS
    jr c,.gen
    scf
    ret

GEN_REACH equ 6             ; pixels from a generator's middle

gen_charge:  ds NUM_GENS*2
gen_state:   ds NUM_GENS
dot_shown:   ds NUM_GENS
gauge_shown: db 0
near_gen:    db 0
gen_tick:    db 0
breaches:    db 0           ; how many times a generator has drained
breach_new:  db 0           ; a bit per generator, set when it drains
