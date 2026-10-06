; Sprite engine: masked, pre-shifted software sprites on the scrolling
; playfield, erased by restoring tiles, with a foreground layer drawn over
; them.
;
; A sprite record is 4 bytes: frame id, world x (16 bits: pixels around the
; planet, 0-1023), y (top line, 0-135). Each frame is stored twice, as drawn
; (W bytes per line) and shifted one pixel right (W+1 bytes), so any x can be
; drawn with whole bytes, both as raw pixels and as a compiled routine (see
; tools/spritec.py), in one of the 6128's extra RAM banks, paged in at
; #4000 while sprites are drawn. Pen 0 is transparent: the generic loop
; takes the AND mask of a sprite byte from mask_table; compiled routines
; carry their masks as immediates.
;
; Each screen buffer keeps the list of records it shows. Before the back
; buffer is drawn again, the cells under its old records are restored from
; the map (only the lines the sprite covered, in whole 4-pixel cells). Then
; the new records are drawn in list order, and the foreground tiles under
; them are drawn again through their masks, so sprites pass behind them.
;
; Sprites are clipped to the left and right edges of the view, not to the
; top and bottom: game code keeps them inside lines 0-143. A sprite row that
; would cross a 256-byte boundary of the screen is drawn in two parts, so
; the inner loop can step with INC L.

MAX_SPRITES equ 16
FRAME_SIZE  equ 12          ; bytes per spr_frames entry
REC_SIZE    equ 4
VIEW_BYTES  equ SCREEN_WORDS*2
COPY_LINE   equ 12          ; bytes of code per line in copy_unroll
OVL_LINE    equ 18          ; bytes of code per line in ovl_unroll
SEG_BYTE    equ 8           ; bytes of code per byte in seg_unroll
LAYOUT_SIZE equ 8           ; bytes of a sprite layout (see layout:)

; Draw the frame's sprites into the back buffer: restore what it showed,
; draw the actors list, then the foreground over them.
macro COPY_LAYOUT
    repeat LAYOUT_SIZE
    ldi
    rend
mend

; HL = the word at table + 2 * A.
macro ENTRY table
    add a,a
    add a,{table}&#FF
    ld l,a
    adc a,{table}>>8
    sub l
    ld h,a
    ld a,(hl)
    inc hl
    ld h,(hl)
    ld l,a
mend

; The game writes the frame's sprite records straight into the back
; buffer's list (back_list: count, then records) before render_sprites.
render_sprites:
    ; restore under what the buffer showed, from the layouts saved then
    ld hl,(back_layouts)
    ld a,(hl)
    inc hl
    or a
    jr z,.restored
.restore:
    push af
    push hl
    push hl
    pop ix
    call restore_rect
    pop hl
    ld de,LAYOUT_SIZE
    add hl,de
    pop af
    dec a
    jr nz,.restore
.restored:
    ld hl,(back_list)
    ld a,(hl)
    ld de,(back_layouts)
    ld (de),a
    or a
    ret z
    inc hl
    inc de
.draw:
    push af
    push de
    push hl
    call rec_load
    call band_layout
    call draw_sprite
    call span_has_fg
    ld (cl_fg),a
    pop hl
    ld bc,REC_SIZE
    add hl,bc
    pop de
    push hl
    ld hl,layout
    COPY_LAYOUT
    pop hl
    pop af
    dec a
    jr nz,.draw
    ld bc,GA_PORT*256+RAM_BASE   ; base RAM back at #4000
    out (c),c
    ; foreground over the sprites that need it
    ld hl,(back_layouts)
    ld b,(hl)
    inc hl
.overlay:
    ld de,LAYOUT_SIZE-1
    add hl,de
    ld a,(hl)               ; cl_fg
    inc hl
    or a
    jr z,.no_fg
    push bc
    push hl
    ld de,-LAYOUT_SIZE
    add hl,de
    push hl
    pop ix
    call overlay_rect
    pop hl
    pop bc
.no_fg:
    djnz .overlay
    ret

; Load the record at HL: sp_x, sp_y and the frame's table entry (sp_w0 on).
rec_load:
    ld a,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    inc hl
    ld (sp_x),bc
    ld c,(hl)
    ld hl,sp_y
    ld (hl),c
    ; frame table entry: FRAME_SIZE (12) bytes
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld e,l
    ld d,h
    add hl,hl
    add hl,de
    ld de,spr_frames
    add hl,de
    ld de,sp_w0
    repeat FRAME_SIZE
    ldi
    rend
    ret

; ---------------------------------------------------------------------------
; Cell work (restore, foreground) over the cells a sprite covers.

; The loaded sprite's map columns: rs_col0 (x / 4) and rs_cols.
rect_span:
    ld hl,(sp_x)
    srl h
    rr l
    srl h
    rr l
    ld a,l
    ld (rs_col0),a
    ld hl,(sp_x)
    ld a,(sp_w0)
    add a,a
    dec a
    add a,l
    ld l,a
    adc a,h
    sub l
    ld h,a
    srl h
    rr l
    srl h
    rr l                    ; last column, mod 256
    ld a,(rs_col0)
    ld c,a
    ld a,l
    sub c
    inc a
    ld (rs_cols),a
    ret

; A non-zero (NZ) if any column of the span has foreground tiles.
span_has_fg:
    ld a,(rs_cols)
    ld b,a
    ld a,(rs_col0)
    ld l,a
    ld h,col_fg>>8
.col:
    ld a,(hl)
    or a
    ret nz
    inc l
    djnz .col
    ret

; The loaded sprite's layout: its span (rect_span) and how its lines fall on
; character rows, the same for each of its columns: a first band from line
; cl_l0 of row cl_r0 (cl_n0 lines), then cl_full whole rows, then a last
; band of cl_nlast lines (maybe 0).
band_layout:
    call rect_span
    ld a,(sp_y)
    ld c,a
    and 7
    ld (cl_l0),a
    ld b,a
    ld a,8
    sub b
    ld b,a
    ld a,(sp_h)
    cp b
    jr c,.first
    ld a,b
.first:
    ld (cl_n0),a
    ld e,a
    ld a,(sp_h)
    sub e
    ld e,a
    rrca
    rrca
    rrca
    and 31
    ld (cl_full),a
    ld a,e
    and 7
    ld (cl_nlast),a
    ld a,c
    rrca
    rrca
    rrca
    and 31
    ld (cl_r0),a
    ret

; The cell loop for restore (kind 0) and foreground (kind 1), for the
; sprite layout at IX: for each visible column under the sprite, walk
; its bands, find each cell's tile and call the copy or overlay code,
; entered so that it does just the band's lines. BC holds the ring address
; of the current row, IX the map cell. The foreground loop skips columns
; without foreground and cells without an overlay.
macro CELL_LOOP kind
    ld a,(ix+2)             ; first line within the first row
    ld c,a
    add a,a
  if {kind}
    add a,a
  endif
    ld (.soff+1),a          ; source offset of that line in a tile / overlay
    ld a,c
    add a,a
    add a,a
    add a,a
    ld (.l8+1),a            ; its screen offset (high byte)
    ld a,(ix+3)
  if {kind}
    ENTRY ovl_entries
  else
    ENTRY copy_entries
  endif
    ld (.go_first+1),hl
    ld a,(ix+4)
    ld (.full+1),a
    ld a,(ix+5)
    ld (.last_on+1),a
  if {kind}
    ENTRY ovl_entries
  else
    ENTRY copy_entries
  endif
    ld (.go_last+1),hl
    ; ring offset of the view's first column on the first row
    ld a,(ix+6)
    ld (.r0+1),a
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
    ld (.base+1),hl
    ld c,(ix+0)
    ld b,(ix+1)
.column:
    push bc
  if {kind}
    ld l,c
    ld h,col_fg>>8
    ld a,(hl)
    or a
    jp z,.next
  endif
    ld a,(back_pos)
    ld e,a
    ld a,c
    sub e                   ; columns right of the view's left edge
    cp SCREEN_WORDS
    jp nc,.next
    add a,a
    ld e,a
    ld d,0
.base:
    ld hl,0
    add hl,de
    ld a,h
    and 7
    ld h,a
    ld a,(back_page)
    or h
    ld b,a
    ld e,c                  ; column
    ld c,l                  ; BC = ring address of the column on the first row
    ld l,e
    ld h,col_ptrs>>8
    ld a,(hl)
    inc h
    ld h,(hl)
.r0:
    add a,0
    ld l,a
    jr nc,.same_page
    inc h
.same_page:
    push hl
    pop ix                  ; the column's map cell on the first row
    ; first band
    ld a,(ix+0)
    inc ix
  if {kind}
    OVL_SRC .skip_first
  else
    TILE_SRC
  endif
    ld a,l
.soff:
    add a,0
    ld l,a
    ld a,b
.l8:
    or 0
    ld d,a
    ld e,c
.go_first:
    call 0
.skip_first:
.full:
    ld a,0
    or a
    jr z,.last
    ld iyl,a
.full_band:
    NEXT_ROW
    ld a,(ix+0)
    inc ix
  if {kind}
    OVL_SRC .skip_full
  else
    TILE_SRC
  endif
    ld d,b
    ld e,c
  if {kind}
    call ovl_unroll
  else
    call copy_unroll
  endif
.skip_full:
    dec iyl
    jr nz,.full_band
.last:
.last_on:
    ld a,0
    or a
    jr z,.next
    NEXT_ROW
    ld a,(ix+0)
  if {kind}
    OVL_SRC .next
  else
    TILE_SRC
  endif
    ld d,b
    ld e,c
.go_last:
    call 0
.next:
    pop bc
    inc c
    dec b
    jp nz,.column
    ret
mend

; Restore the map under the sprite whose layout is at IX, in the back
; buffer: every visible cell column it covers, over the lines it covers.
restore_rect:
    CELL_LOOP 0

; Draw the foreground over the sprite whose layout is at IX, in the back
; buffer.
overlay_rect:
    CELL_LOOP 1

; Entries into copy_unroll / ovl_unroll that do 0-8 lines.
copy_entries:
n=0
    repeat 9
    dw copy_end-n*COPY_LINE
n=n+1
    rend
ovl_entries:
n=0
    repeat 9
    dw ovl_end-n*OVL_LINE
n=n+1
    rend

; One tile line per block, from HL (in a 16-byte aligned tile) to DE (even).
; Keeps BC.
copy_unroll:
    repeat 8
    ld a,(hl)
    ld (de),a
    inc l
    inc e
    ld a,(hl)
    ld (de),a
    inc l
    dec e
    ld a,d
    add 8
    ld d,a
    rend
copy_end:
    ret

; One overlay line per block: (mask, pixels) for each of the 2 bytes, from
; HL (in a 32-byte aligned overlay) to DE (even). Keeps BC.
ovl_unroll:
    repeat 8
    ld a,(de)
    and (hl)
    inc l
    or (hl)
    inc l
    ld (de),a
    inc e
    ld a,(de)
    and (hl)
    inc l
    or (hl)
    inc l
    ld (de),a
    dec e
    ld a,d
    add 8
    ld d,a
    rend
ovl_end:
    ret

; ---------------------------------------------------------------------------
; Masked sprite drawing.

; Draw the loaded sprite into the back buffer; band_layout must have run.
; Pages in the sprite's RAM bank (render_sprites puts base RAM back). A
; whole sprite whose lines stay inside 256-byte pages is drawn by its
; compiled routine; a clipped one (or a rare one whose rows cross a 256-byte
; boundary) by the generic masked loop, from its raw data.
draw_sprite:
    ld a,(sp_bank)
    ld b,GA_PORT
    out (c),a
    ; screen x = world x - view x, as a signed value in -512..511
    ld hl,(back_pos)
    add hl,hl
    add hl,hl
    ex de,hl
    ld hl,(sp_x)
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
    rr l                    ; HL = screen byte column, carry = odd pixel
    ld de,(sp_p0)
    ld bc,(sp_c0)
    ld a,(sp_w0)
    jr nc,.unshifted
    ld de,(sp_p1)
    ld bc,(sp_c1)
    inc a
.unshifted:
    ld (ds_w),a
    ld (ds_code),bc
    ; clip to the view's 80 bytes
    bit 7,h
    jr z,.from_left
    ld a,l                  ; starts left of the view: skip -column bytes
    neg
    ld c,a
    ld a,(ds_w)
    sub c
    ret c
    ret z
    ld (ds_n),a
    xor a
    ld (ds_off),a
    ld a,c
    jr .clipped
.from_left:
    ld a,l
    cp VIEW_BYTES
    ret nc
    ld (ds_off),a
    ld c,a
    ld a,VIEW_BYTES
    sub c
    ld c,a
    ld a,(ds_w)
    cp c
    jr c,.whole
    ld a,c
    ld (ds_n),a
    xor a
    jr .clipped
.whole:
    ld (ds_n),a
    push de
    call ring_offset
    call draw_compiled
    pop de
    ret nc
    jr .generic
.clipped:
    add a,e                 ; source += skipped bytes
    ld e,a
    adc a,d
    sub e
    ld d,a
    push de
    call ring_offset
    pop de
.generic:
    ld a,(ds_n)
    call dl_setup
    ld a,(ds_n)
    ld (db_n+1),a
    ; the bands: as laid out by band_layout
    ld a,(cl_l0)
    add a,a
    add a,a
    add a,a
    ld c,a
    ld a,(cl_n0)
    call draw_band
    ld a,(cl_full)
    or a
    jr z,.last
    ld b,a
.full:
    push bc
    call next_band
    ld a,8
    call draw_band
    pop bc
    djnz .full
.last:
    ld a,(cl_nlast)
    or a
    ret z
    push af
    call next_band
    pop af
    jp draw_band

; ds_o = ring offset of the sprite's first byte on its first row.
ring_offset:
    ld a,(cl_r0)
    add a,a
    add a,row_off&#FF
    ld l,a
    adc a,row_off>>8
    sub l
    ld h,a
    ld a,(hl)
    inc hl
    ld h,(hl)
    ld l,a
    ld a,(ds_off)
    add a,l
    ld l,a
    adc a,h
    sub l
    ld h,a
    ld bc,(back_pos)
    add hl,bc
    add hl,bc
    ld (ds_o),hl
    ret

; Draw the whole sprite with its compiled routine, unless one of its rows
; would run past the end of the 2K screen ring: then return with carry set.
draw_compiled:
    ld a,(cl_full)
    inc a
    ld b,a                  ; rows: the first, the full ones, the last
    ld a,(cl_nlast)
    or a
    jr z,.rows
    inc b
.rows:
    ld a,(ds_w)
    ld c,a
    ld hl,(ds_o)            ; the row's ring offset
    ld de,VIEW_BYTES
.row:
    ld a,h
    and 7
    cp 7
    jr nz,.fits             ; not in the last 256 bytes of the ring
    ld a,l
    add a,c
    jr nc,.fits
    jr z,.fits              ; ends exactly at the end of the ring
    scf
    ret
.fits:
    add hl,de
    djnz .row
    ; HL = page | ring block | first line, ring offset low byte
    ld a,(cl_l0)
    add a,a
    add a,a
    add a,a
    ld c,a
    ld hl,(ds_o)
    ld a,h
    and 7
    or c
    ld c,a
    ld a,(back_page)
    or c
    ld h,a
    ld de,(ds_code)
    ld (.go+1),de
.go:
    call 0
    or a
    ret

; Move ds_o to the next character row; C = 0 (its first line).
next_band:
    ld hl,(ds_o)
    ld a,l
    add a,VIEW_BYTES
    ld l,a
    jr nc,.same
    inc h
.same:
    ld (ds_o),hl
    ld c,0
    ret

; Draw A lines of the sprite from DE (which moves on), starting on line C/8
; of the row at ring offset ds_o.
draw_band:
    ld (ds_cnt),a
    ld iyl,a
    ld hl,(ds_o)
    ld a,h
    and 7
    or c
    ld c,a
    ld a,(back_page)
    or c
    ld h,a
db_n:
    ld a,0                  ; bytes per line
    add a,l
    jp nc,draw_lines
    jp z,draw_lines         ; ends exactly on a 256-byte boundary
    ; crosses one: draw the bytes up to it, then the rest
    ld a,l
    neg
    ld (ds_k),a
    push de
    push hl
    call dl_setup
    pop hl
    push hl
    call draw_lines
    pop hl
    pop bc                  ; source of the band
    push de                 ; source after it
    ld a,(ds_k)
    add a,c
    ld e,a
    adc a,b
    sub e
    ld d,a
    ; screen: the next 256 bytes of the ring, wrapping at #800
    ld a,h
    and 7
    inc a
    and 7
    ld c,a
    ld a,h
    and #F8
    or c
    ld h,a
    ld l,0
    ld a,(ds_k)
    ld c,a
    ld a,(ds_n)
    sub c
    call dl_setup
    ld a,(ds_cnt)
    ld iyl,a
    call draw_lines
    ld a,(ds_n)
    call dl_setup
    pop de
    ret

; Set draw_lines up for A bytes per line. Trashes A and C only.
dl_setup:
    ld (dl_back+1),a
    ld c,a
    ld a,(ds_w)
    sub c
    ld (dl_skip+1),a
    ; no source gap: jump over the skip
    jr nz,.gap
    ld a,dl_step-dl_skip_jr-2
    jr .patch
.gap:
    xor a
.patch:
    ld (dl_skip_jr+1),a
    ld a,c
    add a,a
    add a,a
    add a,a                 ; * SEG_BYTE
    ld c,a
    ld a,seg_end&#FF
    sub c
    ld (dl_go+1),a
    ld a,seg_end>>8
    sbc a,0
    ld (dl_go+2),a
    ret

; Draw IYL sprite lines from DE to HL, stepping W bytes in the source and
; one pixel line (#800) on the screen per line.
draw_lines:
    ld b,mask_table>>8
dl_line:
dl_go:
    jp 0
seg_unroll:
    repeat SPR_MAX_W
    ld a,(de)
    ld c,a
    ld a,(bc)               ; mask for this sprite byte
    and (hl)
    or c
    ld (hl),a
    inc de
    inc l
    rend
seg_end:
    ld a,l
dl_back:
    sub 0
    ld l,a
dl_skip_jr:
    jr dl_skip              ; patched to jump to dl_step when there's no gap
dl_skip:
    ld a,0
    add a,e
    ld e,a
    adc a,d
    sub e
    ld d,a
dl_step:
    ld a,h
    add 8
    ld h,a
    dec iyl
    jr nz,dl_line
    ret

    assert seg_end-seg_unroll == SPR_MAX_W*SEG_BYTE
    assert copy_end-copy_unroll == 8*COPY_LINE
    assert ovl_end-ovl_unroll == 8*OVL_LINE

; Byte offset of each character row in the ring.
row_off:
r=0
    repeat PLAY_ROWS
    dw r*VIEW_BYTES
r=r+1
    rend

; Working variables.
sp_x:    dw 0
sp_y:    db 0
sp_w0:   db 0               ; frame info, FRAME_SIZE bytes as in spr_frames
sp_h:    db 0
sp_p0:   dw 0               ; raw data, unshifted and shifted
sp_p1:   dw 0
sp_c0:   dw 0               ; compiled routines
sp_c1:   dw 0
sp_bank: db 0               ; RAM configuration that pages them in
         db 0
; A sprite's layout (LAYOUT_SIZE bytes, kept per buffer for the restore).
layout:
rs_col0: db 0               ; first map column
rs_cols: db 0               ; columns
cl_l0:   db 0               ; first line within its first row
cl_n0:   db 0               ; lines in the first row
cl_full: db 0               ; whole rows after it
cl_nlast: db 0              ; lines in the last row
cl_r0:   db 0               ; first row
cl_fg:   db 0               ; non-zero if it touches foreground columns
    assert $-layout == LAYOUT_SIZE
ds_w:    db 0
ds_n:    db 0
ds_k:    db 0
ds_off:  db 0
ds_cnt:  db 0
ds_o:    dw 0
ds_code: dw 0

; What each buffer shows: the records, and the layouts drawn.
list_a:  db 0
         ds MAX_SPRITES*REC_SIZE
list_b:  db 0
         ds MAX_SPRITES*REC_SIZE
layouts_a: db 0             ; count, then layouts
         ds MAX_SPRITES*LAYOUT_SIZE
layouts_b: db 0
         ds MAX_SPRITES*LAYOUT_SIZE
