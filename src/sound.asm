; Sound: a small AY-3-8912 music and sound effect driver, ticked at 50 Hz
; by the VSYNC interrupt.
;
; Music plays on all three channels from the streams made by
; tools/gen_music.py (build/sound.inc): notes with durations, instrument
; changes (volume envelopes), loop or end. A sound effect takes channel C
; over while it lasts, one volume, period and noise setting per tick; a new
; effect replaces the playing one if its priority is at least as high.
;
; The game asks for music and effects by writing a byte (music_req,
; sfx_req) that the next tick picks up, so no request is ever half-written
; when the interrupt comes. Effect numbers rise with priority: of two asked
; for in one tick, the higher one wins.
;
; Registers 0-10 are computed into psg_shadow and written out every tick,
; except while the main code is reading the keyboard (psg_busy), which
; goes through the same PSG port; that tick's writes are then skipped and
; the next one catches up.
;
; Everything here runs from the interrupt, possibly while an extra bank is
; paged in at #4000, so code and data stay below #4000.

CH_PTR   equ 0              ; stream position (high byte 0 = channel off)
CH_START equ 2              ; stream start, for looping
CH_WAIT  equ 4              ; ticks left of the current note
CH_NOTE  equ 5              ; 0 = rest
CH_ENV   equ 6              ; envelope position
CH_INST  equ 8              ; envelope of the instrument
CH_SIZE  equ 10

MIXER_TONES equ #38         ; tones on, noise off; bit 6 = 0 keeps port A an input
MUSIC_STOP  equ #FF

    include "../build/sound.inc"

; Silence the AY (interrupts off, or from the interrupt).
sound_init:
    xor a
    ld (chan_a+CH_PTR+1),a
    ld (chan_b+CH_PTR+1),a
    ld (chan_c+CH_PTR+1),a
    ld (sfx_ptr+1),a
    ld (sfx_prio),a
    ld hl,psg_shadow
    ld b,11
.clear:
    ld (hl),a
    inc hl
    djnz .clear
    ld a,MIXER_TONES
    ld (psg_shadow+7),a
    jp psg_write

; Ask for song A (SONG_*, or MUSIC_STOP) at the next tick. Trashes A.
music_play:
    ld (music_req),a
    ret

; Ask for sound effect A (SFX_*) at the next tick, unless a higher one has
; been asked for since the last tick. Trashes F only.
sfx_play:
    push hl
    ld hl,sfx_req
    cp (hl)
    jr c,.keep
    ld (hl),a
.keep:
    pop hl
    ret

; One 50 Hz tick, from the interrupt (AF, BC and HL are saved there).
sound_tick:
    push de
    push ix
    ld a,(music_req)
    or a
    call nz,music_start
    ld a,(sfx_req)
    or a
    call nz,sfx_start
    ld ix,chan_a
    call chan_tick
    ld (psg_shadow+0),hl
    ld (psg_shadow+8),a
    ld ix,chan_b
    call chan_tick
    ld (psg_shadow+2),hl
    ld (psg_shadow+9),a
    ld ix,chan_c
    call chan_tick
    ld (psg_shadow+4),hl
    ld (psg_shadow+10),a
    ld a,MIXER_TONES
    ld (psg_shadow+7),a
    call fx_step
    ld a,(psg_busy)
    or a
    call z,psg_write
    pop ix
    pop de
    ret

; Start song A (1-based), or stop the music for MUSIC_STOP.
music_start:
    ld e,a
    xor a
    ld (music_req),a
    ld a,e
    cp MUSIC_STOP
    jr nz,.song
    xor a
    ld (chan_a+CH_PTR+1),a
    ld (chan_b+CH_PTR+1),a
    ld (chan_c+CH_PTR+1),a
    ret
.song:
    dec a
    ld l,a
    ld h,0
    add hl,hl
    ld e,l
    ld d,h
    add hl,hl
    add hl,de
    ld de,snd_songs
    add hl,de
    ld ix,chan_a
    ld b,3
.chan:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld (ix+CH_PTR),e
    ld (ix+CH_PTR+1),d
    ld (ix+CH_START),e
    ld (ix+CH_START+1),d
    ld (ix+CH_WAIT),1
    ld (ix+CH_NOTE),0
    ld de,snd_inst_lead
    ld (ix+CH_INST),e
    ld (ix+CH_INST+1),d
    ld de,CH_SIZE
    add ix,de
    djnz .chan
    ret

; Start sound effect A if its priority is at least that of the playing one.
sfx_start:
    ld e,a
    xor a
    ld (sfx_req),a
    ld a,e
    dec a
    ld l,a
    ld h,0
    ld e,l
    ld d,h
    add hl,hl
    add hl,de
    ld de,snd_sfx
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld a,(sfx_prio)
    cp (hl)
    jr z,.go
    ret nc
.go:
    ld a,(hl)
    ld (sfx_prio),a
    ld (sfx_ptr),de
    ret

; Channel IX: step its stream and envelope. Out: A = volume, HL = period.
chan_tick:
    ld a,(ix+CH_PTR+1)
    or a
    jp z,.silent
    dec (ix+CH_WAIT)
    jr nz,.envelope
    ld l,(ix+CH_PTR)
    ld h,(ix+CH_PTR+1)
.event:
    ld a,(hl)
    inc hl
    cp #FE
    jr c,.not_control
    jr z,.loop
    ld (ix+CH_PTR+1),0      ; #FF: the end
    jr .silent
.loop:
    ld l,(ix+CH_START)
    ld h,(ix+CH_START+1)
    jr .event
.not_control:
    cp #80
    jr c,.note
    and #7F                 ; instrument
    add a,a
    ld e,a
    ld d,0
    push hl
    ld hl,snd_instruments
    add hl,de
    ld a,(hl)
    inc hl
    ld h,(hl)
    ld (ix+CH_INST),a
    ld (ix+CH_INST+1),h
    pop hl
    jr .event
.note:
    ld (ix+CH_NOTE),a
    ld a,(hl)
    inc hl
    ld (ix+CH_WAIT),a
    ld (ix+CH_PTR),l
    ld (ix+CH_PTR+1),h
    ld a,(ix+CH_INST)
    ld (ix+CH_ENV),a
    ld a,(ix+CH_INST+1)
    ld (ix+CH_ENV+1),a
.envelope:
    ld a,(ix+CH_NOTE)
    or a
    jp z,.silent
    ld l,(ix+CH_ENV)
    ld h,(ix+CH_ENV+1)
    ld c,(hl)               ; this tick's volume
    inc hl
    ld a,(hl)
    cp #FF                  ; hold the last volume
    jr z,.period
    ld (ix+CH_ENV),l
    ld (ix+CH_ENV+1),h
.period:
    ld a,(ix+CH_NOTE)
    dec a
    add a,a
    ld e,a
    ld d,0
    ld hl,snd_periods
    add hl,de
    ld a,(hl)
    inc hl
    ld h,(hl)
    ld l,a
    ld a,c
    ret
.silent:
    xor a
    ld h,a
    ld l,a
    ret

; The playing effect's step, over channel C.
fx_step:
    ld hl,(sfx_ptr)
    ld a,h
    or a
    ret z
    ld a,(hl)
    cp #FF
    jr z,.end
    ld (psg_shadow+10),a
    inc hl
    ld a,(hl)
    ld (psg_shadow+4),a
    inc hl
    ld a,(hl)
    ld c,a
    and #0F
    ld (psg_shadow+5),a
    inc hl
    ld a,(hl)
    ld (psg_shadow+6),a
    inc hl
    ld (sfx_ptr),hl
    ld a,MIXER_TONES
    bit 7,c
    jr z,.no_noise
    and %11011111           ; noise on C
.no_noise:
    bit 6,c
    jr z,.tone
    or %00000100            ; tone off on C
.tone:
    ld (psg_shadow+7),a
    ret
.end:
    xor a
    ld (sfx_ptr+1),a
    ld (sfx_prio),a
    ret

; Write psg_shadow to AY registers 0-10. Trashes A, BC, HL.
psg_write:
    push de
    ld hl,psg_shadow
    ld d,0
.reg:
    ld b,PPI_A
    out (c),d               ; register number
    ld bc,PPI_C*256+#C0     ; latch address
    out (c),c
    ld c,0                  ; inactive
    out (c),c
    ld b,PPI_A
    ld a,(hl)
    out (c),a               ; value
    ld bc,PPI_C*256+#80     ; write
    out (c),c
    ld c,0
    out (c),c
    inc hl
    inc d
    ld a,d
    cp 11
    jr nz,.reg
    pop de
    ret

chan_a:     ds CH_SIZE
chan_b:     ds CH_SIZE
chan_c:     ds CH_SIZE
psg_shadow: ds 11
music_req:  db 0
sfx_req:    db 0
sfx_ptr:    dw 0
sfx_prio:   db 0
psg_busy:   db 0            ; the main code is reading the keyboard
