; Interrupts, CRTC split, rasters, frame flipping and input, with the
; firmware switched off.
;
; The gate array interrupts 6 times per frame (300 Hz), every 52 lines,
; locked to VSYNC. Counting lines from the first playfield line, they land on
; lines 242 (during VSYNC, index 0), 294, 34, 86, 138 and 190.
;
; Each 312-line frame is cut into two CRTC frames (a "rupture"):
;
;   frame A  rows 0-16   lines   0-135  scrolling playfield (double buffered)
;   frame B  rows 0-21   lines 136-311  HUD (8 rows), border, VSYNC at row 13
;
; so VSYNC stays at absolute row 30 and the frame stays 312 lines long. The
; interrupts rewrite R4 (rows in frame), R6 (rows shown), R7 (VSYNC row) and
; R12/R13 (start address) for the frame to come. Each write is made while
; the row counter is past the value written, so no comparison fires early,
; and R12/R13 are never written on row 0, where CRTC 1 reloads them:
;
;   index 1 (B row 19): R6 = 25, R7 = 30 (never reached), R12/R13 = playfield
;   index 3 (A row 10): R4 = 16, R6 = 8, R12/R13 = HUD
;   index 4 (B row 0):  R7 = 13
;   index 5 (B row 6):  R4 = 21
;
; The VSYNC interrupt also ticks the sound driver (sound.asm) at 50 Hz.
; screen_off and screen_on black the picture out while the screens are
; redrawn: the interrupts load their palettes through pf_pal_src and
; hud_pal_src.
;
; Rasters: the sky pen changes colour on lines 36 and 88, timed to land in
; the horizontal blank. The HUD palette is loaded by the interrupt on line
; 138, which is HUD line 2: the HUD's first 8 lines use pen 0 only, so the
; load can run through them without a wait. The VSYNC interrupt puts the
; playfield palette back.
;
; Flips: when the main loop has queued a buffer and at least 2 frames have
; passed since the last flip, the VSYNC interrupt takes its address, and
; index 1 hands it to the CRTC for the next frame. That locks the game to
; 25 fps.

INTS_PER_FRAME equ 6
INT_UNSYNCED   equ 6        ; int_idx value until the first VSYNC is seen

PLAY_ROWS   equ 17
HUD_ROWS    equ 8
TOTAL_ROWS  equ 39
VSYNC_ROW   equ 30

R4_A equ PLAY_ROWS-1
R4_B equ TOTAL_ROWS-PLAY_ROWS-1
R6_A equ 25
R6_B equ HUD_ROWS
R7_A equ 30
R7_B equ VSYNC_ROW-PLAY_ROWS

HUD_R12 equ #10             ; page #4000, offset 0
HUD_R13 equ 0

SKY_PEN equ 1

; Delays (in NOPs) that put each raster change in the horizontal blank,
; measured with tests/calibrate_rasters.py. With no delay the sky change
; lands 14 us into the line after the interrupt's; 38 more puts it at 52 us,
; mid-blank (the picture is 0-40 us), so the new colour starts on lines 36
; and 88, with 6 us of margin either way for interrupt latency.
SKY1_DELAY equ 38
SKY2_DELAY equ 38

; Write A to CRTC register reg. Trashes BC.
macro CRTC_SET reg
    ld bc,CRTC_SEL*256+{reg}
    out (c),c
    inc b
    out (c),a
mend

; Burn exactly n NOPs (n >= 5). Trashes B.
macro WAIT_NOPS n
    ld b,({n}-1)>>2
    djnz $
    defs ({n}-1)&3,0
mend

isr:
    push af
    push bc
    push hl
    ld b,PPI_B
    in a,(c)
    rra
    jp c,isr_vsync
    ld hl,int_idx
    inc (hl)
    ld a,(hl)
    cp INTS_PER_FRAME
    jr c,.dispatch
    ld (hl),INT_UNSYNCED
    ; lost the frame: if it went mid-split, frame A's settings (R7 past its
    ; end) would leave the CRTC without a VSYNC to find it again by, for
    ; good; a plain whole frame has one
    ld a,TOTAL_ROWS-1
    CRTC_SET 4
    ld a,VSYNC_ROW
    CRTC_SET 7
    jp isr_exit
.dispatch:
    add a,a
    ld l,a
    ld h,0
    ld bc,isr_table-2
    add hl,bc
    ld a,(hl)
    inc hl
    ld h,(hl)
    ld l,a
    jp (hl)

isr_table:
    dw isr_1, isr_2, isr_3, isr_4, isr_5

isr_vsync:
    ; the generator core colour the frame just ended was shown with, and the
    ; one loaded below for the next (for tests: pen 2 changes as it likes)
    ld a,(core_now)
    ld (core_prev),a
    ld a,(pf_palette+CORE_PEN)
    ld (core_now),a
    xor a
    ld (int_idx),a
    ld hl,(frame_count)
    inc hl
    ld (frame_count),hl
    ld hl,frames_since_flip
    inc (hl)
    ld a,(flip_pending)
    or a
    jr z,.palette
    ld a,(hl)
    cp 2
    jr c,.palette
    jr z,.on_time
    ld hl,(late_flips)
    inc hl
    ld (late_flips),hl
.on_time:
    ld hl,(next_crtc)
    ld (pf_crtc),hl
    ld hl,(flips)
    inc hl
    ld (flips),hl
    xor a
    ld (frames_since_flip),a
    ld (flip_pending),a
.palette:
    ; the screen is in its bottom border: put the playfield palette back
    ld hl,(pf_pal_src)
    ld bc,GA_PORT*256+1
    repeat 15
    out (c),c
    ld a,(hl)
    out (c),a
    inc hl
    inc c
    rend
    ld c,SKY_PEN
    out (c),c
    ld a,(sky_colours)
    out (c),a
    call sound_tick
    jp isr_exit

; B row 18: set up frame A.
isr_1:
    ld a,(split_on)
    or a
    jr z,.start
    ld a,R6_A
    CRTC_SET 6
    ld a,R7_A
    CRTC_SET 7
.start:
    ld a,(pf_crtc+1)
    CRTC_SET 12
    ld a,(pf_crtc)
    CRTC_SET 13
    jp isr_exit

; Line 34: second sky band.
isr_2:
    ld bc,GA_PORT*256+SKY_PEN
    out (c),c
    ld a,(sky_colours+1)
    WAIT_NOPS SKY1_DELAY+5
    ld b,GA_PORT
    out (c),a
    jp isr_exit

; Line 86: third sky band; frame A ends after row 16, frame B shows 8 rows
; of the HUD.
isr_3:
    ld bc,GA_PORT*256+SKY_PEN
    out (c),c
    ld a,(sky_colours+2)
    WAIT_NOPS SKY2_DELAY+5
    ld b,GA_PORT
    out (c),a
    ld a,(split_on)
    or a
    jp z,isr_exit
    ld a,R4_A
    CRTC_SET 4
    ld a,R6_B
    CRTC_SET 6
    ld a,HUD_R12
    CRTC_SET 12
    ld a,HUD_R13
    CRTC_SET 13
    jp isr_exit

; Line 138 (HUD line 2): frame B gets VSYNC on its row 13; the HUD palette
; goes in while the HUD's blank top lines are shown.
isr_4:
    ld a,(split_on)
    or a
    jp z,isr_exit
    ld a,R7_B
    CRTC_SET 7
    ld hl,(hud_pal_src)
    ld bc,GA_PORT*256+1
    repeat 15           ; pens 1-15, one every 13 us
    out (c),c
    ld a,(hl)
    out (c),a
    inc hl
    inc c
    rend
    jp isr_exit

; B row 6: frame B ends after its row 21.
isr_5:
    ld a,(split_on)
    or a
    jp z,isr_exit
    ld a,R4_B
    CRTC_SET 4
isr_exit:
    pop hl
    pop bc
    pop af
    ei
    ret

; Queue the back buffer for display and wait until the flip has happened.
; The wait loop counts its turns (IDLE_LOOP NOPs each, interrupts aside),
; which measures the time left over in the frame. Interrupts stay enabled:
; a DI here would delay the raster interrupts.
IDLE_LOOP equ 10

flip_and_wait:
    ld a,1
    ld (flip_pending),a
    ld de,0
.wait:
    inc de
    ld a,(flip_pending)
    or a
    jr nz,.wait
    ld (idle_last),de
    ld hl,(idle_min)
    or a
    sbc hl,de
    ret c
    ld (idle_min),de
    ret

; Program the CRTC for a standard full screen at start address DE (D = R12),
; before the split takes over.
crtc_init:
    ld a,38
    CRTC_SET 4
    ld a,25
    CRTC_SET 6
    ld a,30
    CRTC_SET 7
    ld a,d
    CRTC_SET 12
    ld a,e
    CRTC_SET 13
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

; Collect joystick 0 and the keys into joy_state (1 = pressed): bit 0 up,
; 1 down, 2 left, 3 right (joystick or cursor keys), 4 fire (either
; joystick button or space), 5 whistle (W), 6 pause (P), 7 music (M);
; Esc into esc_down (non-zero when down).
read_input:
    ld a,1
    ld (psg_busy),a         ; the sound interrupt keeps off the PSG meanwhile
    ld a,KB_LINE_JOY0
    call read_kb_line
    cpl
    ld e,a
    and %00110000           ; both fire buttons count as fire
    jr z,.no_button
    set 4,e
.no_button:
    ld a,e
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
    ld a,KB_LINE_W
    call read_kb_line
    bit 3,a
    jr nz,.no_whistle
    set 5,e
.no_whistle:
    ld a,KB_LINE_P
    call read_kb_line
    bit 3,a
    jr nz,.no_pause
    set 6,e
.no_pause:
    ld a,KB_LINE_M
    call read_kb_line
    bit 6,a
    jr nz,.no_music
    set 7,e
.no_music:
    ld a,KB_LINE_ESC
    call read_kb_line
    cpl
    and 4
    ld (esc_down),a
    ld a,e
    ld (joy_state),a
    xor a
    ld (psg_busy),a
    ret

; Wait for the next VSYNC.
wait_frame:
    ld hl,frame_count
    ld a,(hl)
.wait:
    cp (hl)
    jr z,.wait
    ret

; Black the picture out (all pens, sky bands, HUD) from the next frame on,
; and wait until a whole black frame has started.
screen_off:
    ld a,(screen_is_off)
    or a
    jr nz,.wait
    inc a
    ld (screen_is_off),a
    ld hl,sky_colours
    ld de,sky_saved
    ld bc,3
    ldir
    ld hl,black_pal+1
    ld (pf_pal_src),hl
    ld (hud_pal_src),hl
    ld a,#54
    ld (sky_colours),a
    ld (sky_colours+1),a
    ld (sky_colours+2),a
.wait:
    call wait_frame
    jp wait_frame

; Show the picture again, from the next frame.
screen_on:
    ld a,(screen_is_off)
    or a
    ret z
    xor a
    ld (screen_is_off),a
    ld hl,sky_saved
    ld de,sky_colours
    ld bc,3
    ldir
    ld hl,pf_palette+1
    ld (pf_pal_src),hl
    ld hl,hud_palette+1
    ld (hud_pal_src),hl
    ret

; Load the 16 pens from HL and set the border to black.
set_palette:
    ld bc,GA_PORT*256+0
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
    ld a,#54
    out (c),a
    ret

frame_count:       dw 0
flips:             dw 0
late_flips:        dw 0
int_idx:           db INT_UNSYNCED
frames_since_flip: db 0
flip_pending:      db 0
split_on:          db 0
core_now:          db 0
core_prev:         db 0
next_crtc:         dw 0     ; queued playfield address: low byte R13, high byte R12
pf_crtc:           dw 0     ; playfield address for the next frame A
idle_last:         dw 0     ; idle loop turns before the last flip
idle_min:          dw #FFFF ; the fewest seen
joy_state:         db 0
esc_down:          db 0
pf_pal_src:        dw black_pal+1   ; pens 1-15 the interrupts load
hud_pal_src:       dw black_pal+1
screen_is_off:     db 1             ; off until the first planet is in
sky_saved:         ds 3
black_pal:         ds 16,#54

; Sky pen colour for lines 0-33, 34-85 and 86-143.
sky_colours:       db #54, #54, #54  ; the planet's (screen_on), or black
