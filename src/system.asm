; Interrupts, frame flipping and input, with the firmware switched off.
;
; The gate array interrupts 6 times per frame (300 Hz); the one that lands
; during VSYNC starts a new frame. Flips happen there: when the main loop
; has queued a buffer and at least 2 frames have passed since the last flip,
; the handler writes R12/R13, which the CRTC picks up at the next frame start
; on every CRTC type. That locks the game to 25 fps.

INTS_PER_FRAME equ 6

isr:
    push af
    push bc
    push hl
    ld b,PPI_B
    in a,(c)
    rra
    jr nc,.not_vsync
    xor a
    ld (int_idx),a
    ld hl,(frame_count)
    inc hl
    ld (frame_count),hl
    ld hl,frames_since_flip
    inc (hl)
    ld a,(flip_pending)
    or a
    jr z,.done
    ld a,(hl)
    cp 2
    jr c,.done
    jr z,.on_time
    ld hl,(late_flips)
    inc hl
    ld (late_flips),hl
.on_time:
    ld bc,CRTC_SEL*256+12
    out (c),c
    ld a,(next_crtc+1)
    inc b
    out (c),a
    dec b
    inc c
    out (c),c
    ld a,(next_crtc)
    inc b
    out (c),a
    ld hl,(flips)
    inc hl
    ld (flips),hl
    xor a
    ld (frames_since_flip),a
    ld (flip_pending),a
    jr .done
.not_vsync:
    ld hl,int_idx
    inc (hl)
.done:
    pop hl
    pop bc
    pop af
    ei
    ret

; Queue the back buffer for display and wait until the flip has happened.
; Also records how long the frame's work took, in 1/300 s units.
flip_and_wait:
    di
    ld a,(frames_since_flip)
    ld b,a
    add a,a
    add a,b
    add a,a             ; * INTS_PER_FRAME
    ld b,a
    ld a,(int_idx)
    add a,b
    ld (work_ints),a
    ld b,a
    ld a,(work_ints_max)
    cp b
    jr nc,.keep
    ld a,b
    ld (work_ints_max),a
.keep:
    ld a,1
    ld (flip_pending),a
    ei
.wait:
    ld a,(flip_pending)
    or a
    jr nz,.wait
    ret

; Read keyboard matrix line A. Returns the line's bits in A (0 = pressed).
read_kb_line:
    ld bc,PPI_A*256+14  ; PSG register 14 (port A, the keyboard)
    out (c),c
    ld bc,PPI_C*256+#C0 ; PSG: latch address
    out (c),c
    ld bc,PPI_C*256+0   ; PSG: inactive
    out (c),c
    ld bc,PPI_CTRL*256+#92  ; PPI port A to input
    out (c),c
    or #40              ; PSG: read, plus the matrix line
    ld b,PPI_C
    out (c),a
    ld b,PPI_A
    in a,(c)
    ld bc,PPI_CTRL*256+#82  ; PPI port A back to output
    out (c),c
    ld bc,PPI_C*256+0
    out (c),c
    ret

; Collect joystick 0 and the cursor keys into joy_state:
; bit0 up, 1 down, 2 left, 3 right, 4 fire (1 = pressed).
read_input:
    ld a,KB_LINE_JOY0
    call read_kb_line
    cpl
    and %00011111
    ld e,a
    ld a,KB_LINE_CURSOR1
    call read_kb_line
    cpl
    bit 0,a
    jr z,.no_up
    set 0,e
.no_up:
    bit 1,a
    jr z,.no_right
    set 3,e
.no_right:
    bit 2,a
    jr z,.no_down
    set 1,e
.no_down:
    ld a,KB_LINE_CURSOR2
    call read_kb_line
    rra
    jr c,.no_left
    set 2,e
.no_left:
    ld a,KB_LINE_SPACE
    call read_kb_line
    rla
    jr c,.no_fire
    set 4,e
.no_fire:
    ld a,e
    ld (joy_state),a
    ret

; Load the 16 pens from HL and set the border to pen 0's colour.
set_palette:
    ld b,GA_PORT
    ld c,0
.pen:
    out (c),c
    ld a,(hl)
    out (c),a
    inc hl
    inc c
    ld a,c
    cp 16
    jr c,.pen
    out (c),c           ; pen 16 = border
    ld a,(palette_data)
    out (c),a
    ret

frame_count:       dw 0
flips:             dw 0
late_flips:        dw 0
int_idx:           db 0
frames_since_flip: db 0
flip_pending:      db 0
next_crtc:         dw 0     ; low byte R13, high byte R12
work_ints:         db 0
work_ints_max:     db 0
joy_state:         db 0
