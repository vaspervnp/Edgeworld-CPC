; The title screen and the high scores.
;
; The title shows the planet with the logo over its sky (draw_logo) and,
; in the HUD, a panel that changes every PAGE_FRAMES between how to play
; and the high-score table, with PRESS FIRE flashing under it. The game
; starts when fire is pressed and let go.
;
; A score above the table's last asks for initials: up and down choose a
; letter, fire takes it. The table lives only in memory.
;
; Runs with base RAM paged in (it lives in the HUD page's spare space).

PANEL_LINE  equ 10          ; the panel: HUD lines 10-55
PANEL_LINES equ 46
FIRE_LINE   equ 50
PAGE_FRAMES equ 400         ; 8 seconds a page
HS_COUNT    equ 5
HS_SIZE     equ 5           ; score (word), 3 letters
HS_LINE     equ 19          ; first table line, then every 6
REPEAT_WAIT equ 15          ; frames before up/down repeats...
REPEAT_GAP  equ 5           ; ...and between repeats

; Show the title until the player starts a game.
title_screen:
    call screen_off
    ld hl,TITLE_POS
    call scroll_init
    ld a,CORE_STABLE
    ld (pf_palette+CORE_PEN),a
    call draw_logo
    call panel_clear
    call draw_page
    ld a,SONG_TITLE
    call music_play
    call screen_on
    ld a,1                  ; fire held from before does not count
    ld (fire_prev),a
    ld hl,0
    ld (title_time),hl
    ld a,ST_TITLE
    ld (game_state),a
.frame:
    call wait_frame
    call read_input
    ld a,(joy_state)
    and 1<<IN_FIRE
    ld hl,fire_prev
    ld b,(hl)
    ld (hl),a
    jr z,.timers
    ld a,b
    or a
    jr z,.start
.timers:
    ld hl,(title_time)
    inc hl
    ld (title_time),hl
    ld a,l
    and 31
    jr z,.fire_on
    cp 20
    call z,fire_off
    ld de,PAGE_FRAMES
    or a
    sbc hl,de
    jr nz,.frame
    ld (title_time),hl
    ld a,(title_page)
    xor 1
    ld (title_page),a
    call draw_page
    jr .frame
.fire_on:
    call fire_on
    jr .frame
.start:
    ; wait for fire to be let go
    call wait_frame
    call read_input
    ld a,(joy_state)
    and 1<<IN_FIRE
    jr nz,.start
    ld a,MUSIC_STOP
    jp music_play

panel_clear:
    ld a,PANEL_LINE
    ld b,PANEL_LINES
    jp hud_clear

; The page of the panel in title_page, PRESS FIRE included.
draw_page:
    ld a,PANEL_LINE
    ld b,FIRE_LINE-PANEL_LINE
    call hud_clear
    call fire_on
    ld a,(title_page)
    or a
    ld hl,how_to_play
    jp z,text_lines
    ; the high scores
    ld hl,hs_title
    call text_lines
    ld ix,hs_table
    ld b,0                  ; entry
.entry:
    push bc
    ; "N. ABC  nnnnn0"
    ld a,b
    add a,'1'
    ld (line_buf),a
    ld a,'.'
    ld (line_buf+1),a
    ld a,' '
    ld (line_buf+2),a
    ld (line_buf+6),a
    ld (line_buf+7),a
    ld a,(ix+2)
    ld (line_buf+3),a
    ld a,(ix+3)
    ld (line_buf+4),a
    ld a,(ix+4)
    ld (line_buf+5),a
    ld l,(ix+0)
    ld h,(ix+1)
    call num_to_text
    ld hl,num_buf
    ld de,line_buf+8
    ld bc,5
    ldir
    ld a,'0'
    ld (de),a
    inc de
    xor a
    ld (de),a
    pop bc
    push bc
    ld a,(hs_new)           ; the newest entry stands out
    cp b
    ld c,PEN_DIGITS
    jr nz,.pen
    ld c,PEN_GOOD
.pen:
    ld a,b                  ; line HS_LINE + 6 * entry
    add a,a
    add a,b
    add a,a
    add a,HS_LINE
    ld de,line_buf
    call draw_centred
    ld de,HS_SIZE
    add ix,de
    pop bc
    inc b
    ld a,b
    cp HS_COUNT
    jr c,.entry
    ret

fire_on:
    ld a,FIRE_LINE
    ld de,msg_press_fire
    ld c,PEN_LABEL
    jp draw_centred

fire_off:
    push hl
    ld a,FIRE_LINE
    ld b,5
    call hud_clear
    pop hl
    ret

; After a game: a score that makes the table is entered, with initials.
hiscore_check:
    ld a,#FF
    ld (hs_new),a
    xor a
    ld (title_page),a
    ; find the first entry the score beats
    ld ix,hs_table
    ld b,0
.find:
    ld hl,(score)
    ld e,(ix+0)
    ld d,(ix+1)
    or a
    sbc hl,de
    jr z,.below
    jr nc,.found
.below:
    ld de,HS_SIZE
    add ix,de
    inc b
    ld a,b
    cp HS_COUNT
    jr c,.find
    ret                     ; not good enough
.found:
    ld a,b
    ld (hs_new),a
    ld a,1
    ld (title_page),a
    ; move the entries below it down one (from the bottom up)
    ld a,HS_COUNT-1
    sub b
    jr z,.place
    ld c,a
    ld b,0
    ld h,b                  ; bytes = entries * HS_SIZE
    ld l,c
    add hl,hl
    add hl,hl
    add hl,bc
    ld b,h
    ld c,l
    ld hl,hs_table+(HS_COUNT-1)*HS_SIZE-1
    ld de,hs_table+HS_COUNT*HS_SIZE-1
    lddr
.place:
    ld hl,(score)
    ld (ix+0),l
    ld (ix+1),h
    ld (ix+2),'A'
    ld (ix+3),' '
    ld (ix+4),' '
    jp name_entry

; Initials for the entry at IX.
name_entry:
    ld a,ST_ENTRY
    ld (game_state),a
    call panel_clear
    ld hl,entry_text
    call text_lines
    ld a,(joy_state)        ; what is held already does not count
    ld (fire_prev),a
    xor a
    ld (letter),a
    ld (blink),a
.frame:
    call wait_frame
    call read_input
    ld a,(fire_prev)
    cpl
    ld c,a
    ld a,(joy_state)
    ld (fire_prev),a
    and c                   ; just pressed
    ld c,a
    ; up and down: on pressing, then repeating while held
    ld a,(joy_state)
    and (1<<IN_UP)|(1<<IN_DOWN)
    jr z,.no_repeat
    ld b,a
    ld a,c
    and (1<<IN_UP)|(1<<IN_DOWN)
    ld a,REPEAT_WAIT
    jr nz,.step
    ld hl,rep_timer
    dec (hl)
    jr nz,.fire
    ld a,REPEAT_GAP
.step:
    ld (rep_timer),a
    call letter_ptr
    ld a,(hl)
    bit IN_UP,b
    call nz,next_letter
    bit IN_DOWN,b
    call nz,prev_letter
    ld (hl),a
    xor a
    ld (blink),a
    jr .fire
.no_repeat:
.fire:
    bit IN_FIRE,c
    jr z,.show
    ld hl,letter
    inc (hl)
    ld a,(hl)
    cp 3
    jr nc,.done
    call letter_ptr
    ld (hl),'A'
    xor a
    ld (blink),a
.show:
    ld hl,blink
    inc (hl)
    call draw_name
    jr .frame
.done:
    xor a
    ld (blink),a
    jp draw_name

; HL = the letter being chosen. Trashes A, DE.
letter_ptr:
    push ix
    pop hl
    inc hl
    inc hl
    ld a,(letter)
    ld e,a
    ld d,0
    add hl,de
    ret

; The letter after / before A: A-Z, then '.'.
next_letter:
    cp '.'
    jr z,.first
    cp 'Z'
    jr z,.dot
    inc a
    ret
.first:
    ld a,'A'
    ret
.dot:
    ld a,'.'
    ret

prev_letter:
    cp 'A'
    jr z,.dot
    cp '.'
    jr z,.last
    dec a
    ret
.dot:
    ld a,'.'
    ret
.last:
    ld a,'Z'
    ret

; The initials, the one being chosen flashing (blink).
draw_name:
    ld a,(ix+2)
    ld (line_buf),a
    ld a,(ix+3)
    ld (line_buf+1),a
    ld a,(ix+4)
    ld (line_buf+2),a
    xor a
    ld (line_buf+3),a
    ld a,(letter)
    cp 3
    jr nc,.draw
    ld a,(blink)
    and 16
    jr z,.draw
    ld a,(letter)
    ld e,a
    ld d,0
    ld hl,line_buf
    add hl,de
    ld (hl),'_'
.draw:
    ld a,NAME_LINE
    ld de,line_buf
    ld c,PEN_DIGITS
    jp draw_centred

NAME_LINE equ 34

how_to_play:
    db 12, PEN_LABEL, "KEEP THE FOUR SHIELD GENERATORS",0
    db 18, PEN_LABEL, "CHARGED UNTIL THE TIME RUNS OUT",0
    db 26, PEN_DIGITS, "JOYSTICK OR CURSOR KEYS, SPACE FIRES",0
    db 33, PEN_DIGITS, "FIRE+DOWN GETS OFF AND ON, W WHISTLES",0
    db 40, PEN_GOOD, "HOLD DOWN AT A GENERATOR TO CHARGE",0
    db #FF
hs_title:
    db 12, PEN_LABEL, "HIGH SCORES",0
    db #FF
entry_text:
    db 14, PEN_GOOD, "A NEW HIGH SCORE!",0
    db 24, PEN_LABEL, "ENTER YOUR INITIALS",0
    db 46, PEN_DIM, "UP/DOWN CHOOSES, FIRE TAKES",0
    db #FF
msg_press_fire: db "PRESS FIRE TO START",0

hs_table:
    dw 300 : db "SHD"
    dw 250 : db "RUN"
    dw 200 : db "CPC"
    dw 150 : db "AMS"
    dw 100 : db "ZAP"
hs_new:     db #FF          ; the entry just made, for the table's colours
title_page: db 0            ; 0 how to play, 1 high scores
title_time: dw 0
fire_prev:  db 0            ; input bits of the last frame
letter:     db 0            ; initial being chosen
blink:      db 0
rep_timer:  db 0
