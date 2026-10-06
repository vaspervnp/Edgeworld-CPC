; Loading planets from disc. The firmware is long gone by then, so this
; drives the uPD765 floppy controller itself: it reads the AMSDOS directory
; (data format: 9 sectors of 512 bytes a track, IDs #C1-#C9, 1K blocks from
; track 0), finds PLANETn.BIN's blocks, reads them into the screen pages
; (blacked out, and redrawn afterwards), then copies the file past its
; AMSDOS header into extra bank 7 and the planet's header into base RAM.
;
; Interrupts are off while it runs: a byte comes every 32 us and must be
; taken in time. The CRTC gets a plain frame with no rows shown meanwhile;
; afterwards the interrupt waits for a VSYNC and takes the split up again.
; A read that fails starts the whole load again, with the border flashing.
;
; It pages bank 7 in, so it stays below #4000.

FDC_MSR    equ #FB7E        ; main status register
FDC_MOTOR  equ #FA7E
LOAD_BUF   equ #8000        ; directory, then the file
DIR_SECTORS equ 4           ; 64 entries of 32 bytes
FIRST_SECTOR equ #C1
TRACK_SECTORS equ 9
MAX_BLOCKS equ 32

; Load planet A (1-9) and make it current. The picture must be off.
load_planet:
    ld (current_planet),a
    add a,'0'
    ld (planet_name+6),a
    di
    call sound_init             ; nothing left droning meanwhile
    ld de,(pf_crtc)
    call crtc_init              ; a plain frame...
    xor a
    CRTC_SET 6                  ; ...with nothing shown
    ld bc,FDC_MOTOR
    ld a,1
    out (c),a
    call spin_up
    jr .start
.retry:
    ld bc,GA_PORT*256+#10       ; a read failed: flash the border, try again
    out (c),c
    ld a,(load_tries)
    rra
    ld a,#4C                    ; bright red
    jr c,.border
    ld a,#54
.border:
    out (c),a
.start:
    ld hl,load_tries
    inc (hl)
    call fdc_recalibrate
    ; the directory
    ld hl,LOAD_BUF
    ld de,FIRST_SECTOR          ; track 0
    ld b,DIR_SECTORS
.dir:
    push bc
    call read_sector
    pop bc
    jr c,.retry
    inc e
    djnz .dir
    call find_blocks
    jr c,.retry
    ; the file
    ld hl,LOAD_BUF
    ld ix,blocks
    ld a,(nblocks)
    ld b,a
.block:
    push bc
    ld a,(ix+0)
    inc ix
    call read_block
    pop bc
    jr c,.retry
    djnz .block
    ld bc,FDC_MOTOR
    xor a
    out (c),a
    ld (load_tries),a
    ld bc,GA_PORT*256+#10       ; black border again
    out (c),c
    ld a,#54
    out (c),a
    ; into bank 7, past the 128-byte AMSDOS header; the header and the
    ; foreground columns into base RAM
    PAGE MAP_BANK
    ld hl,LOAD_BUF+128
    ld de,#4000
    ld bc,#4000
    ldir
    ld hl,PLANET_HDR
    ld de,planet
    ld bc,PLANET_SIZE
    ldir
    ld hl,PLANET_COL_FG
    ld de,col_fg
    ld bc,256
    ldir
    PAGE RAM_BASE
    ld hl,planet_sky            ; screen_on puts the sky colours back from there
    ld de,sky_saved
    ld bc,3
    ldir
    ld a,INT_UNSYNCED           ; the interrupt waits for a VSYNC
    ld (int_idx),a
    ei
    ret

; About half a second for the motor to get up to speed.
spin_up:
    ld b,3
.outer:
    ld de,0
.inner:
    dec de
    ld a,d
    or e
    jr nz,.inner
    djnz .outer
    ret

; blocks / nblocks = the blocks of planet_name, extent by extent.
; Carry if there is no such file.
find_blocks:
    xor a
    ld (nblocks),a
    ld hl,blocks
    ld (blk_ptr),hl
    ld c,0                      ; the extent wanted
.extent:
    ld ix,LOAD_BUF
    ld b,64
.entry:
    ld a,(ix+0)                 ; user 0 (#E5: deleted)
    or a
    jr nz,.next
    ld a,(ix+12)
    cp c
    jr nz,.next
    push bc
    push ix
    pop hl
    inc hl
    ld de,planet_name
    ld b,11
.name:
    ld a,(de)
    xor (hl)
    and #7F                     ; bit 7 of the extension: attributes
    jr nz,.differs
    inc hl
    inc de
    djnz .name
    pop bc                      ; this extent: take its blocks
    jr .take
.differs:
    pop bc
.next:
    ld de,32
    add ix,de
    djnz .entry
    ld a,(nblocks)              ; no more extents: done, if any
    cp 1
    ret
.take:
    push bc
    push ix
    pop hl
    ld de,16
    add hl,de
    ld de,(blk_ptr)
    ld b,16
.block:
    ld a,(hl)
    inc hl
    or a
    jr z,.none
    ld (de),a
    inc de
    ld a,(nblocks)
    inc a
    ld (nblocks),a
    cp MAX_BLOCKS
    jr nc,.full
.none:
    djnz .block
.full:
    ld (blk_ptr),de
    pop bc
    inc c
    jr .extent

; Read 1K block A (2 sectors) to HL; HL moves on. Carry on error.
read_block:
    ld e,a
    ld d,0
    ex de,hl
    add hl,hl                   ; its first logical sector
    ex de,hl
    call read_logical
    ret c
    inc de
; Read logical sector DE (track * 9 + sector) to HL; DE kept.
read_logical:
    push de
    ld b,0
.divide:
    ld a,e
    sub TRACK_SECTORS
    ld e,a
    ld a,d
    sbc a,0
    ld d,a
    jr c,.divided
    inc b
    jr .divide
.divided:
    ld a,e
    add a,TRACK_SECTORS+FIRST_SECTOR
    ld e,a
    ld d,b
    call read_sector
    pop de
    ret

; Read sector E of track D to HL; HL moves on 512. Carry on error.
read_sector:
    ld a,(cur_track)
    cp d
    call nz,fdc_seek
    ld a,#46                    ; read data, MFM
    call fdc_put
    xor a                       ; drive A, head 0
    call fdc_put
    ld a,d                      ; C
    call fdc_put
    xor a                       ; H
    call fdc_put
    ld a,e                      ; R
    call fdc_put
    ld a,2                      ; N: 512 bytes
    call fdc_put
    ld a,e                      ; EOT: this sector only
    call fdc_put
    ld a,#2A                    ; GPL
    call fdc_put
    ld a,#FF                    ; DTL
    call fdc_put
    ld bc,FDC_MSR
.byte:
    in a,(c)
    jp p,.byte                  ; not ready
    and #20
    jr z,.result                ; execution over
    inc c
    in a,(c)
    ld (hl),a
    inc hl
    dec c
    jr .byte
.result:
    push hl
    call fdc_results
    pop hl
    ; with no terminal count line on the CPC, a good read ends with ST1's
    ; end of cylinder bit: anything else is an error
    ld a,(fdc_res+1)
    and #7F
    ld b,a
    ld a,(fdc_res+2)
    or b
    ret z
    scf
    ret

; Seek to track D.
fdc_seek:
    ld a,#0F
    call fdc_put
    xor a
    call fdc_put
    ld a,d
    call fdc_put
    call fdc_wait_seek
    ld a,d
    ld (cur_track),a
    ret

fdc_recalibrate:
    ld a,#07
    call fdc_put
    xor a
    call fdc_put
    call fdc_wait_seek
    xor a
    ld (cur_track),a
    ret

; Sense interrupt status until the seek has ended. Keeps HL, DE.
fdc_wait_seek:
    push hl
.sense:
    ld a,#08
    call fdc_put
    call fdc_results
    ld a,(fdc_res)
    and #20                     ; seek end
    jr z,.sense
    pop hl
    ret

; Send A to the controller. Trashes BC.
fdc_put:
    push af
    ld bc,FDC_MSR
.wait:
    in a,(c)
    add a,a                     ; ready into carry, direction into sign
    jr nc,.wait
    jp m,.wait
    pop af
    inc c
    out (c),a
    ret

; Take the result bytes into fdc_res. Trashes A, BC, HL.
fdc_results:
    ld hl,fdc_res
.next:
    ld bc,FDC_MSR
.wait:
    in a,(c)
    add a,a
    jr nc,.wait
    ret p                       ; the controller wants a command: done
    inc c
    in a,(c)
    ld (hl),a
    inc hl
    ex (sp),hl                  ; let the status settle
    ex (sp),hl
    jr .next

planet_name:    db "PLANET1 BIN"
current_planet: db 0
cur_track:      db 0
load_tries:     db 0
fdc_res:        ds 8
nblocks:        db 0
blk_ptr:        dw 0
blocks:         ds MAX_BLOCKS
