; The course of a game: starting one, the countdown and the score in the
; HUD, and the end: energy gone, the shield down (SHIELD_FAILS generators
; drained at once) or the time up with the shield still standing, which clears the planet
; and earns a bonus. The end message stays up in the HUD for END_FRAMES
; while the world goes on without the player.
;
; Runs with base RAM paged in (it lives in the HUD page's spare space).

FPS          equ 25         ; game frames a second
END_FRAMES   equ 125        ; the end message's game frames before the high scores
END_ENERGY   equ 1          ; game_over: the rider's energy ran out (enemies.asm)
END_SHIELD   equ 2          ; every generator drained
END_CLEAR    equ 3          ; the time ran out with the shield up

ST_BOOT      equ 0          ; game_state, for tests
ST_TITLE     equ 1
ST_PLAY      equ 2
ST_ENTRY     equ 3

ROW_A_LINE   equ 33         ; HUD text rows (tools/gen_hud.py)
ROW_B_LINE   equ 41
ROW_C_LINE   equ 49
TIME_BYTE    equ 14         ; "M:SS" after "TIME "
SCORE_BYTE   equ 50         ; 5 digits after "SCORE ", then a fixed 0
PEN_DIGITS   equ 4          ; HUD pens: bright white
PEN_LABEL    equ 6          ; bright yellow
PEN_GOOD     equ 5          ; bright green
PEN_BAD      equ 7          ; bright red
PEN_DIM      equ 2          ; grey

; Set up a new game on the planet and show it.
game_start:
    call screen_off
    xor a
    ld (end_timer),a
    call hud_init
    call player_init
    call hud_spares
    call gen_init
    call enemies_init
    ld hl,(rand_seed)       ; when fire was pressed makes each game different
    ld a,(frame_count)
    xor l
    ld l,a
    or h
    jr nz,.seeded
    inc l
.seeded:
    ld (rand_seed),hl
    ld hl,PLANET_TIME
    ld (time_secs),hl
    ld a,FPS
    ld (time_tick),a
    ld hl,#FFFF
    ld (score_shown),hl
    call draw_time
    call draw_score
    ld hl,0
    call scroll_init
    call hud_update
    xor a
    ld (frames_since_flip),a
    ld a,ST_PLAY
    ld (game_state),a
    ld a,SONG_GAME
    call music_play
    jp screen_on

; One game frame of the game's course, after the frame's work.
; Out: Z while the game goes on, NZ when it is over and its message has
; been up long enough.
game_tick:
    ld a,(end_timer)
    or a
    jr nz,.ending
    call draw_score
    ld a,(game_over)
    or a
    jr nz,.end
    ; the shield fails when SHIELD_FAILS generators are drained
    ld hl,gen_state
    ld bc,NUM_GENS*256
.gen:
    ld a,(hl)
    cp GS_DRAINED
    jr nz,.up
    inc c
.up:
    inc hl
    djnz .gen
    ld a,c
    cp SHIELD_FAILS
    jr c,.shield_up
    ld a,END_SHIELD
    jr .end_as
.shield_up:
    ld hl,time_tick
    dec (hl)
    jr nz,.going
    ld (hl),FPS
    ld hl,(time_secs)
    dec hl
    ld (time_secs),hl
    call draw_time
    ld hl,(time_secs)
    ld a,h
    or l
    jr z,.time_up
    ld a,h                  ; tick through the last 10 seconds
    or a
    jr nz,.going
    ld a,l
    cp 11
    jr nc,.going
    ld a,SFX_TICK
    call sfx_play
.going:
    xor a
    ret
.time_up:
    ld a,END_CLEAR
.end_as:
    ld (game_over),a
.end:
    ld a,END_FRAMES
    ld (end_timer),a
    ld a,(game_over)
    cp END_CLEAR
    ld a,SONG_OVER
    jr nz,.music
    call clear_enemies
    call add_bonus
    ld a,SONG_CLEAR
.music:
    call music_play
    ld a,ROW_A_LINE         ; the message a row a frame, to stay in time
    call end_row
    xor a
    ret
.ending:
    ld a,(end_timer)
    cp END_FRAMES
    ld b,ROW_B_LINE
    jr z,.row
    cp END_FRAMES-1
    ld b,ROW_C_LINE
    jr nz,.count
.row:
    ld a,b
    call end_row
.count:
    ld hl,end_timer
    dec (hl)
    jr z,.over
    xor a
    ret
.over:
    or 1
    ret

; The time left as M:SS after "TIME ".
draw_time:
    ld hl,(time_secs)
    ld c,'0'
    ld de,-60
.minutes:
    add hl,de
    jr nc,.seconds
    inc c
    jr .minutes
.seconds:
    ld de,60
    add hl,de
    ld a,c
    ld (num_buf),a
    ld a,':'
    ld (num_buf+1),a
    ld a,l
    ld c,'0'
.tens:
    sub 10
    jr c,.units
    inc c
    jr .tens
.units:
    add a,10+'0'
    ld (num_buf+3),a
    ld a,c
    ld (num_buf+2),a
    xor a
    ld (num_buf+4),a
    ld a,ROW_A_LINE
    ld c,TIME_BYTE
    call hud_addr
    ld de,num_buf
    ld a,PEN_DIGITS
    jp draw_text

; The score after "SCORE ", if it changed.
draw_score:
    ld hl,(score)
    ld de,(score_shown)
    or a
    sbc hl,de
    ret z
    ld hl,(score)
    ld (score_shown),hl
    call num_to_text
    ld a,ROW_A_LINE
    ld c,SCORE_BYTE
    call hud_addr
    ld de,num_buf
    ld a,PEN_DIGITS
    jp draw_text

; Planet clear: every enemy and missile goes up in smoke.
clear_enemies:
    ld ix,enemies
    ld b,MAX_ENEMIES
.enemy:
    ld a,(ix+0)
    or a
    jr z,.next
    cp E_HOSTILE
    jr nc,.next
    ld (ix+0),E_BOOM
    ld (ix+5),8
    ld (ix+7),0
.next:
    ld de,EN_SIZE
    add ix,de
    djnz .enemy
    ld hl,missiles
    ld b,MAX_MISSILES*MS_SIZE
.missile:
    ld (hl),0
    inc hl
    djnz .missile
    ld a,SFX_BOOM
    jp sfx_play

; Planet clear bonus: the energy left, plus a quarter of the generators'
; charge (high bytes). Added to the score (which is shown times 10).
add_bonus:
    ld hl,gen_charge+1
    ld de,0
    ld b,NUM_GENS
.gen:
    ld a,(hl)
    add a,e
    ld e,a
    jr nc,.carried
    inc d
.carried:
    inc hl
    inc hl
    djnz .gen
    srl d
    rr e
    srl d
    rr e
    ld a,(pl_energy)
    add a,e
    ld e,a
    jr nc,.sum
    inc d
.sum:
    ld (bonus),de
    ld hl,(score)
    add hl,de
    jr nc,.score
    ld hl,#FFFF
.score:
    ld (score),hl
    ret

; Row A (line) of the end message in the HUD, over the row's text.
end_row:
    push af
    ld b,5
    call hud_clear
    pop af
    ld b,a
    ld a,(game_over)
    ld e,a
    ld a,b
    cp ROW_A_LINE
    jr z,.headline
    cp ROW_B_LINE
    jr z,.second
    ld hl,(score)
    ld de,msg_score
    jr .number
.headline:
    ld c,PEN_BAD
    ld a,e
    cp END_CLEAR
    ld a,b
    ld de,msg_game_over
    jp nz,draw_centred
    ld c,PEN_GOOD
    ld de,msg_clear
    jp draw_centred
.second:
    ld a,e
    cp END_CLEAR
    jr z,.bonus
    cp END_SHIELD
    ld de,msg_shield
    jr z,.why
    ld de,msg_energy
.why:
    ld a,b
    ld c,PEN_LABEL
    jp draw_centred
.bonus:
    ld a,b
    ld hl,(bonus)
    ld de,msg_bonus
; "LABEL nnnnn0" centred on line A: label DE, number HL.
.number:
    push af
    push de
    call num_to_text
    pop hl                  ; label, then the number, then a 0
    ld de,line_buf
.label:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    or a
    jr nz,.label
    dec de
    ld hl,num_buf
    ld bc,5
    ldir
    ld a,'0'
    ld (de),a
    inc de
    xor a
    ld (de),a
    pop af
    ld de,line_buf
    ld c,PEN_DIGITS
    jp draw_centred

msg_game_over: db "GAME OVER",0
msg_energy:    db "THE RIDER HAS FALLEN",0
msg_shield:    db "THE SHIELD HAS FAILED",0
msg_clear:     db "PLANET CLEAR!",0
msg_bonus:     db "BONUS ",0
msg_score:     db "SCORE ",0

time_secs:   dw 0           ; seconds left
time_tick:   db 0           ; game frames to the next second
end_timer:   db 0           ; game frames of the end message left (0: playing)
score_shown: dw 0
bonus:       dw 0
game_state:  db ST_BOOT
line_buf:    ds 41
