; Enemies, their missiles, explosions and energy cells; spawning; collisions
; with the rider's bolts and with the player.
;
;   drifter   floats towards the player, explodes against them
;   tracker   flies high, keeps over the player, drops bombs
;   crawler   walks the ground towards the player (jump it)
;   thrower   stands on the ground, lobs rocks that land at the player
;   carrier   the breach carrier: comes when two generators are drained,
;             takes 12 bolts, bombs from above
;
; A spawner keeps a few enemies coming in from the edges of the view, from
; the planet's mix (planet.asm); a breach sends a wave from the generator
; that drained. Killed enemies explode, and some leave an energy cell that
; falls to the ground: touching it gives the rider energy.
;
; Hits: mounted, the Runner takes them (RUNNER_HITS and it dies, throwing
; the rider off) and the rider loses a little energy; on foot the rider
; loses a lot, and is knocked off a generator. After a hit the player
; flickers and cannot be hit for a moment. No energy left: game_over.
;
; x positions are world pixels (0-1023), y the top line.

MAX_ENEMIES   equ 6
EN_SIZE       equ 8         ; type, x (2), y, hp, timer, anim, drop
MAX_MISSILES  equ 4
MS_SIZE       equ 7         ; type, x (2), y * 4 (2), dx, dy * 4

E_NONE        equ 0
E_DRIFTER     equ 1
E_TRACKER     equ 2
E_CRAWLER     equ 3
E_THROWER     equ 4
E_CARRIER     equ 5
E_BOOM        equ 6         ; an explosion
E_CELL        equ 7         ; an energy cell
E_HOSTILE     equ E_BOOM    ; types below this fight

M_BOMB        equ 1
M_ROCK        equ 2

GROUND_LINE   equ 98        ; the crust
CRAWLER_Y     equ GROUND_LINE-8
THROWER_Y     equ GROUND_LINE-12
CELL_Y        equ GROUND_LINE-6
FLY_MIN_Y     equ 4
FLY_MAX_Y     equ 80
TRACKER_Y     equ 14
CARRIER_Y     equ 8

MAX_ENERGY    equ 100
CELL_ENERGY   equ 25
MOUNTED_DAMAGE equ 4        ; rider energy lost when the Runner is hit
RUNNER_HITS   equ 3
INVULN_FRAMES equ 40
SPAWN_EVERY   equ 60        ; frames between spawns
AMBIENT_MAX   equ 4         ; enemies the spawner keeps around
WAVE_SIZE     equ 3
CARRIER_REST  equ 250       ; frames before another carrier may come
DESPAWN_DIST  equ 320       ; pixels from the player: gone (not the carrier)
CRAWL_PAST    equ 40        ; a crawler turns back this far past the player
TRACK_SWING   equ 28        ; trackers sweep this far either side of it
; (defined up here: rasm loses the sign of -NAME when NAME comes later)
THROW_RANGE   equ 80        ; a thrower lobs at a player this near (higher
                            ; lobs would leave the top of the screen)

; Per type: first frame, width, height, hit points, damage on foot, points.
TYPE_SIZE equ 6
type_table:
    db SPR_DRIFTER0, 8, 10, 1, 12, 1
    db SPR_TRACKER0, 8, 8, 2, 10, 2
    db SPR_CRAWLER0, 8, 8, 2, 12, 2
    db SPR_THROWER0, 8, 12, 3, 12, 3
    db SPR_CARRIER0, 16, 16, 12, 20, 20
    db SPR_BOOM0, 8, 8, 0, 0, 0
    db SPR_CELL, 4, 6, 0, 0, 0

; IY = the type table entry of type A.
macro TYPE_ENTRY
    dec a
    ld e,a
    add a,a
    add a,e
    add a,a                 ; * TYPE_SIZE
    add a,type_table&#FF
    ld e,a
    adc a,type_table>>8
    sub e
    ld d,a
    push de
    pop iy
mend

enemies_init:
    ld hl,enemies
    ld bc,MAX_ENEMIES*EN_SIZE+MAX_MISSILES*MS_SIZE-1
    ld (hl),0
    ld d,h
    ld e,l
    inc de
    ldir
    ld a,MAX_ENERGY
    ld (pl_energy),a
    xor a
    ld (pl_invuln),a
    ld (rn_hits),a
    ld (game_over),a
    ld (carrier_alive),a
    ld (carrier_cool),a
    ld a,#FF
    ld (energy_shown),a
    ld a,SPAWN_EVERY
    ld (spawn_timer),a
    jp energy_bar

; One game frame of enemies, missiles, spawning and collisions.
enemies_update:
    ld hl,en_tick
    inc (hl)
    call player_box
    call spawn_update
    ; move each enemy
    ld ix,enemies
    ld b,MAX_ENEMIES
.enemy:
    push bc
    ld a,(ix+0)
    or a
    call nz,update_enemy
    pop bc
    ld de,EN_SIZE
    add ix,de
    djnz .enemy
    call update_missiles
    call collide_shots
    call collide_player
    ld hl,carrier_cool
    ld a,(hl)
    or a
    jr z,.cool
    dec (hl)
.cool:
    jp energy_bar

; The player's hit box (pb_x, pb_y, pb_w, pb_h) and middle (pl_mid_x/y).
player_box:
    ld hl,(pl_x)
    TO_PIXELS
    ld a,(pl_mode)
    cp MODE_FOOT
    jr z,.foot
    cp MODE_CHARGING
    jr z,.foot
    inc hl
    inc hl
    ld (pb_x),hl
    ld de,6
    add hl,de
    ld (pl_mid_x),hl
    call jump_offset
    neg
    add a,MOUNTED_Y+2
    ld (pb_y),a
    add a,11
    ld (pl_mid_y),a
    ld hl,12+22*256
    ld (pb_w),hl
    ret
.foot:
    inc hl
    ld (pb_x),hl
    ld de,3
    add hl,de
    ld (pl_mid_x),hl
    ld a,RIDER_Y
    ld (pb_y),a
    add a,6
    ld (pl_mid_y),a
    ld hl,6+12*256
    ld (pb_w),hl
    ret

; HL = the player's middle x - (the enemy at IX's x + A, signed), wrapped
; to -512..511. Sets the flags of H (sign: P player to the right).
dx_to_player:
    ld e,a
    rla
    sbc a,a
    ld d,a
    ld l,(ix+1)
    ld h,(ix+2)
    add hl,de
    ex de,hl
    ld hl,(pl_mid_x)
    or a
    sbc hl,de
    ld a,h
    and 3
    bit 1,a
    jr z,.positive
    or #FC
.positive:
    ld h,a
    or a
    ret

; Move the enemy at IX up to A pixels across towards the player.
step_x:
    ld c,a
    ld b,0
; Move it up to C pixels across, to put its middle B pixels (signed) from
; the player's.
step_x_by:
    ld a,(iy+1)
    srl a                   ; half its width: its middle
    sub b
    call dx_to_player
    ld a,h
    or l
    ret z
    bit 7,h
    jr nz,.left
    ; right by min(C, distance)
    ld a,h
    or a
    jr nz,.full_right
    ld a,l
    cp c
    jr c,.right
.full_right:
    ld a,c
.right:
    ld e,a
    ld d,0
    jr .move
.left:
    ld a,h
    inc a
    jr nz,.full_left
    ld a,l
    neg
    cp c
    jr c,.left_by
.full_left:
    ld a,c
.left_by:
    neg
    ld e,a
    ld d,#FF
.move:
    ld l,(ix+1)
    ld h,(ix+2)
    add hl,de
    ld a,h
    and 3
    ld (ix+2),a
    ld (ix+1),l
    ret

; Move the enemy at IX one line up or down towards the player's middle
; (less A), within the flying range.
step_y:
    ld c,a
    ld a,(pl_mid_y)
    sub c
    cp (ix+3)
    ret z
    ld a,(ix+3)
    jr c,.up
    inc a
    cp FLY_MAX_Y+1
    ret nc
    ld (ix+3),a
    ret
.up:
    dec a
    cp FLY_MIN_Y
    ret c
    ld (ix+3),a
    ret

; |player middle - enemy middle| in pixels (capped at 255) -> A, using the
; width at IY.
abs_dx:
    ld a,(iy+1)
    srl a
    call dx_to_player
    bit 7,h
    jr z,.positive
    ex de,hl
    ld hl,0
    or a
    sbc hl,de
.positive:
    ld a,h
    or a
    ld a,l
    ret z
    ld a,255
    ret

update_enemy:
    ld a,(ix+0)
    TYPE_ENTRY
    ; far behind the player: gone (the carrier never gives up)
    ld a,(ix+0)
    cp E_CARRIER
    jr nc,.near
    ld a,(iy+1)
    srl a
    call dx_to_player
    bit 7,h
    jr z,.distance
    ex de,hl
    ld hl,0
    or a
    sbc hl,de
.distance:
    ld de,DESPAWN_DIST
    or a
    sbc hl,de
    jr c,.near
    ld (ix+0),E_NONE
    ret
.near:
    ld a,(ix+0)
    dec a
    add a,a
    ld e,a
    ld d,0
    ld hl,update_table
    add hl,de
    ld a,(hl)
    inc hl
    ld h,(hl)
    ld l,a
    jp (hl)

update_table:
    dw update_drifter, update_tracker, update_crawler, update_thrower
    dw update_carrier, update_boom, update_cell

update_drifter:
    ld a,1
    call step_x
    ld a,(en_tick)
    rra
    ret c                   ; every other frame...
    ld a,5
    jp step_y               ; ...a line nearer

; Trackers sweep to and fro across the player, TRACK_SWING pixels either
; side, each on its own phase, bombing as they pass overhead.
update_tracker:
    inc (ix+6)
    ld b,TRACK_SWING
    bit 6,(ix+6)
    jr z,.side
    ld b,-TRACK_SWING
.side:
    ld c,2
    call step_x_by
    ld a,(ix+5)
    or a
    jr z,.ready
    dec (ix+5)
    ret
.ready:
    call abs_dx
    cp 6
    ret nc
    ; right overhead: a bomb
    ld (ix+5),40
    ld de,3
    ld c,8
    ld hl,M_BOMB+12*256     ; dy 3 lines a frame
    ld b,0
    jp launch

; Crawlers walk at the player and on past them, turning back once they are
; CRAWL_PAST pixels beyond: the player has to jump them (or get off and
; shoot: a mounted bolt flies over them).
update_crawler:
    ld a,(ix+6)             ; its direction: 1, -1, or 0 to choose
    or a
    jr nz,.walking
.turn:
    ld a,(iy+1)
    srl a
    call dx_to_player
    ld a,1
    bit 7,h
    jr z,.set
    ld a,-1
.set:
    ld (ix+6),a
.walking:
    ld a,(iy+1)
    srl a
    call dx_to_player       ; HL = player - crawler
    ld a,(ix+6)
    bit 7,a
    jr nz,.going_left
    bit 7,h
    jr z,.step              ; the player is still ahead
    ld de,CRAWL_PAST
    add hl,de
    bit 7,h
    jr nz,.turn
    jr .step
.going_left:
    bit 7,h
    jr nz,.step
    ld de,-CRAWL_PAST-1
    add hl,de
    bit 7,h
    jr z,.turn
.step:
    ld a,(ix+6)
    ld e,a
    rla
    sbc a,a
    ld d,a
    ld l,(ix+1)
    ld h,(ix+2)
    add hl,de
    ld a,h
    and 3
    ld (ix+2),a
    ld (ix+1),l
    ret



update_thrower:
    ld a,(ix+5)
    or a
    jr z,.ready
    dec (ix+5)
    ret
.ready:
    ld (ix+5),60
    call abs_dx
    cp THROW_RANGE
    ret nc
    cp 16
    ret c                   ; too close to lob at
    ; dx 2 pixels a frame: in the air |dx| / 2 frames, so to land there
    ; start going up |dx| / 4 quarter-lines a frame (gravity 1/4 line)
    srl a
    srl a
    cp 8
    jr nc,.not_low
    ld a,8
.not_low:
    neg
    push af
    ld a,(iy+1)
    srl a
    call dx_to_player
    pop af
    ld b,2
    bit 7,h
    jr z,.throw
    ld b,-2
.throw:
    ld h,a                  ; dy
    ld l,M_ROCK
    ld de,4
    ld c,0
    jp launch

update_carrier:
    ld a,(en_tick)
    rra
    ld a,1
    call nc,step_x
    ld a,(ix+5)
    or a
    jr z,.ready
    dec (ix+5)
    ret
.ready:
    call abs_dx
    cp 24
    ret nc
    ld (ix+5),24
    ld de,7
    ld c,16
    ld hl,M_BOMB+12*256
    ld b,0
    jp launch

update_boom:
    dec (ix+5)
    ret nz
    ld a,(ix+7)
    or a
    jr nz,.cell
    ld (ix+0),E_NONE
    ret
.cell:
    ; leave an energy cell where it was
    ld (ix+0),E_CELL
    ld (ix+5),250
    ld l,(ix+1)
    ld h,(ix+2)
    inc hl
    inc hl
    ld a,h
    and 3
    ld (ix+2),a
    ld (ix+1),l
    ret

update_cell:
    ld a,(ix+3)
    cp CELL_Y
    jr nc,.landed
    add a,2
    cp CELL_Y
    jr c,.fall
    ld a,CELL_Y
.fall:
    ld (ix+3),a
.landed:
    dec (ix+5)
    ret nz
    ld (ix+0),E_NONE
    ret

; Launch missile L (type) with dy H (quarter lines a frame) and dx B, from
; the enemy at IX offset by E pixels across and C lines down.
launch:
    push hl
    ld hl,missiles
    ld d,MAX_MISSILES
.slot:
    ld a,(hl)
    or a
    jr z,.free
    push de
    ld de,MS_SIZE
    add hl,de
    pop de
    dec d
    jr nz,.slot
    pop hl
    ret
.free:
    push hl
    pop iy                  ; the slot
    pop hl                  ; H = dy, L = type
    ld (iy+0),l
    ld (iy+6),h
    ld (iy+5),b
    ld a,(ix+1)
    add a,e
    ld (iy+1),a
    ld a,(ix+2)
    adc a,0
    and 3
    ld (iy+2),a
    ld a,(ix+3)
    add a,c
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld (iy+3),l
    ld (iy+4),h
    ret

; Move the missiles; rocks fall faster each frame; gone at the ground or
; off the view.
update_missiles:
    ld ix,missiles
    ld b,MAX_MISSILES
.missile:
    ld a,(ix+0)
    or a
    jr z,.next
    ; y
    ld a,(ix+6)
    ld e,a
    rla
    sbc a,a
    ld d,a
    ld l,(ix+3)
    ld h,(ix+4)
    add hl,de
    bit 7,h
    jr nz,.gone             ; above the top
    ld (ix+3),l
    ld (ix+4),h
    ld de,GROUND_LINE*4
    or a
    sbc hl,de
    jr nc,.gone
    ld a,(ix+0)
    cp M_ROCK
    jr nz,.across
    inc (ix+6)              ; gravity
.across:
    ld a,(ix+5)
    ld e,a
    rla
    sbc a,a
    ld d,a
    ld l,(ix+1)
    ld h,(ix+2)
    add hl,de
    ld a,h
    and 3
    ld h,a
    ld (ix+1),l
    ld (ix+2),h
    ; off the view?
    ld de,(scroll_pos)
    ex de,hl
    add hl,hl
    add hl,hl
    ex de,hl
    or a
    sbc hl,de
    ld a,h
    and 3
    jr z,.next              ; within 256 pixels right of the view's left
    cp 3
    jr nz,.gone
    ld a,l
    cp (-8)&#FF
    jr nc,.next
.gone:
    ld (ix+0),0
.next:
    ld de,MS_SIZE
    add ix,de
    djnz .missile
    ret

; ---------------------------------------------------------------------------
; Spawning.

spawn_update:
    ld a,(spawn_on)
    or a
    ret z
    ld a,(breach_new)
    or a
    call nz,breach_wave
    call carrier_check
    ld hl,spawn_timer
    dec (hl)
    ret nz
    ld (hl),SPAWN_EVERY
    call count_hostile
    cp AMBIENT_MAX
    ret nc
    ; a type from the planet's mix, from either edge of the view
    call rand
    and 7
    ld e,a
    ld d,0
    ld hl,enemy_mix
    add hl,de
    ld a,(hl)
    push af
    call rand
    ld hl,(scroll_pos)
    add hl,hl
    add hl,hl
    ld de,-24
    rra
    jr nc,.left
    ld de,168
.left:
    add hl,de
    pop af
    call spawn_y
    jp spawn

; C = where type A starts: its line on the ground, or a random height.
spawn_y:
    ld c,CRAWLER_Y
    cp E_CRAWLER
    ret z
    ld c,THROWER_Y
    cp E_THROWER
    ret z
    ld c,TRACKER_Y
    cp E_TRACKER
    ret z
    ld c,CARRIER_Y
    cp E_CARRIER
    ret z
    push af
    push hl
    call rand
    pop hl
    and 63
    add a,16
    ld c,a
    pop af
    ret

; Start an enemy of type A at x HL, y C, if there is a free slot (carry:
; there is none).
spawn:
    push hl
    ld hl,enemies
    ld de,EN_SIZE
    ld b,MAX_ENEMIES
.slot:
    push af
    ld a,(hl)
    or a
    jr z,.free
    pop af
    add hl,de
    djnz .slot
    pop hl
    scf
    ret
.free:
    pop af
    push hl
    pop ix
    pop hl
    ld (ix+0),a
    ld (ix+1),l
    ld a,h
    and 3
    ld (ix+2),a
    ld (ix+3),c
    ld a,(ix+0)
    TYPE_ENTRY
    ld a,(iy+3)
    ld (ix+4),a
    ld (ix+5),30
    xor a
    ld (ix+7),a
    ld (ix+6),a
    ld a,(ix+0)
    cp E_TRACKER
    ret nz
    push hl
    call rand
    pop hl
    ld (ix+6),a             ; its own phase
    ret

; A = enemies that fight.
count_hostile:
    ld hl,enemies
    ld de,EN_SIZE
    ld b,MAX_ENEMIES
    ld c,0
.slot:
    ld a,(hl)
    or a
    jr z,.next
    cp E_HOSTILE
    jr nc,.next
    inc c
.next:
    add hl,de
    djnz .slot
    ld a,c
    ret

; A generator drained: a wave from it, drifters and crawlers in turn.
breach_wave:
    ld c,a
    xor a
    ld (breach_new),a
    ld ix,gen_table
    ld b,NUM_GENS
.gen:
    srl c
    jr nc,.next
    push bc
    push ix
    ld l,(ix+0)
    ld h,0
    add hl,hl
    add hl,hl
    ld de,-8
    add hl,de
    ld b,WAVE_SIZE
.one:
    push bc
    push hl
    ld a,b
    and 1
    ld a,E_DRIFTER
    ld c,40
    jr nz,.spawn
    ld a,E_CRAWLER
    ld c,CRAWLER_Y
.spawn:
    call spawn
    pop hl
    ld de,12
    add hl,de
    pop bc
    djnz .one
    pop ix
    pop bc
.next:
    ld de,GEN_ENTRY
    add ix,de
    djnz .gen
    ret

; Two generators drained and no carrier about: one comes.
carrier_check:
    ld a,(carrier_alive)
    or a
    ret nz
    ld a,(carrier_cool)
    or a
    ret nz
    ld hl,gen_state
    ld b,NUM_GENS
    ld c,0
.gen:
    ld a,(hl)
    cp GS_DRAINED
    jr nz,.next
    inc c
.next:
    inc hl
    djnz .gen
    ld a,c
    cp 2
    ret c
    ld hl,(scroll_pos)
    add hl,hl
    add hl,hl
    ld de,-32
    add hl,de
    ld a,E_CARRIER
    ld c,CARRIER_Y
    call spawn
    ret c
    ld a,1
    ld (carrier_alive),a
    ret

; 16-bit xorshift: A and HL = the next pseudo-random number.
rand:
    ld hl,(rand_seed)
    ld a,h
    rra
    ld a,l
    rra
    xor h
    ld h,a
    ld a,l
    rra
    ld a,h
    rra
    xor l
    ld l,a
    xor h
    ld h,a
    ld (rand_seed),hl
    ret

; ---------------------------------------------------------------------------
; Collisions.

; Box A (ca_x word, ca_y, ca_w, ca_h) and box B (cb_...) overlap: carry.
; ax - bx in (-aw, bw), i.e. (ax - bx + aw) mod 1024 < aw + bw across the
; planet's wrap; the same for y without the wrap.
overlap:
    ld hl,(ca_x)
    ld de,(cb_x)
    or a
    sbc hl,de
    ld a,(ca_w)
    ld e,a
    ld d,0
    add hl,de
    ld a,h
    and 3
    ret nz                  ; no carry
    ld a,(cb_w)
    add a,e
    ld e,a
    ld a,l
    cp e
    ret nc
    ld a,(cb_y)
    ld e,a
    ld a,(ca_y)
    sub e
    ld hl,ca_h
    add a,(hl)
    ld e,a
    ld a,(cb_h)
    add a,(hl)
    ld d,a
    ld a,e
    cp d
    ret

; Box B = the enemy at IX (type entry at IY).
enemy_box_b:
    ld l,(ix+1)
    ld h,(ix+2)
    ld (cb_x),hl
    ld a,(ix+3)
    ld (cb_y),a
    ld a,(iy+1)
    ld (cb_w),a
    ld a,(iy+2)
    ld (cb_h),a
    ret

; The rider's bolts against the enemies.
collide_shots:
    ld hl,shots
    ld b,MAX_SHOTS
.shot:
    ld a,(hl)
    or a
    jr z,.next_shot
    push bc
    push hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld (ca_x),de
    ld a,(hl)
    ld (ca_y),a
    ld a,4
    ld (ca_w),a
    ld (ca_h),a
    ld ix,enemies
    ld b,MAX_ENEMIES
.enemy:
    ld a,(ix+0)
    or a
    jr z,.next_enemy
    cp E_HOSTILE
    jr nc,.next_enemy
    push bc
    TYPE_ENTRY
    call enemy_box_b
    call overlap
    pop bc
    jr nc,.next_enemy
    ; hit: the bolt is spent
    pop hl
    push hl
    ld (hl),0
    dec (ix+4)
    call z,kill_enemy
    jr .shot_done
.next_enemy:
    ld de,EN_SIZE
    add ix,de
    djnz .enemy
.shot_done:
    pop hl
    pop bc
.next_shot:
    ld de,SHOT_SIZE
    add hl,de
    djnz .shot
    ret

; The enemy at IX (type entry IY) is destroyed: points, an explosion,
; maybe an energy cell after it.
kill_enemy:
    ld a,(iy+5)
    ld hl,(score)
    ld e,a
    ld d,0
    add hl,de
    ld (score),hl
    ld a,(ix+0)
    cp E_CARRIER
    jr nz,.not_carrier
    xor a
    ld (carrier_alive),a
    ld a,CARRIER_REST
    ld (carrier_cool),a
    ld (ix+7),1             ; always leaves a cell
    ; the explosion in its middle
    ld l,(ix+1)
    ld h,(ix+2)
    ld de,4
    add hl,de
    ld a,h
    and 3
    ld (ix+2),a
    ld (ix+1),l
    ld a,(ix+3)
    add a,4
    ld (ix+3),a
    jr .boom
.not_carrier:
    call rand
    and 3
    ld a,0
    jr nz,.drop
    inc a
.drop:
    ld (ix+7),a
.boom:
    ld (ix+0),E_BOOM
    ld (ix+5),8
    ret

; The player against enemies, missiles and cells.
collide_player:
    ld hl,(pb_x)
    ld (ca_x),hl
    ld hl,(pb_y)            ; pb_y, then pb_w
    ld a,l
    ld (ca_y),a
    ld a,h
    ld (ca_w),a
    ld a,(pb_h)
    ld (ca_h),a
    ld ix,enemies
    ld b,MAX_ENEMIES
.enemy:
    ld a,(ix+0)
    or a
    jr z,.next
    push bc
    TYPE_ENTRY
    call enemy_box_b
    call overlap
    pop bc
    jr nc,.next
    ld a,(ix+0)
    cp E_CELL
    jr z,.cell
    cp E_HOSTILE
    jr nc,.next
    push bc
    ld a,(iy+4)
    call player_hit
    pop bc
    ld a,(ix+0)
    cp E_DRIFTER
    jr nz,.next
    ; a drifter goes up with it
    ld (ix+0),E_BOOM
    ld (ix+5),8
    ld (ix+7),0
    jr .next
.cell:
    ld (ix+0),E_NONE
    ld a,(pl_energy)
    add a,CELL_ENERGY
    cp MAX_ENERGY+1
    jr c,.energy
    ld a,MAX_ENERGY
.energy:
    ld (pl_energy),a
.next:
    ld de,EN_SIZE
    add ix,de
    djnz .enemy
    ; missiles
    ld ix,missiles
    ld b,MAX_MISSILES
.missile:
    ld a,(ix+0)
    or a
    jr z,.next_missile
    ld l,(ix+1)
    ld h,(ix+2)
    ld (cb_x),hl
    ld l,(ix+3)
    ld h,(ix+4)
    srl h
    rr l
    srl h
    rr l
    ld a,l
    ld (cb_y),a
    ld a,4
    ld (cb_w),a
    ld (cb_h),a
    push bc
    call overlap
    pop bc
    jr nc,.next_missile
    ld (ix+0),0
    push bc
    ld a,MISSILE_DAMAGE
    call player_hit
    pop bc
.next_missile:
    ld de,MS_SIZE
    add ix,de
    djnz .missile
    ret

MISSILE_DAMAGE equ 10

; The player is hit for A energy on foot.
player_hit:
    ld b,a
    ld a,(god_mode)
    or a
    ret nz
    ld a,(pl_invuln)
    or a
    ret nz
    ld a,INVULN_FRAMES
    ld (pl_invuln),a
    ld a,(pl_mode)
    cp MODE_FOOT
    jr z,.energy
    cp MODE_CHARGING
    jr z,.unplug
    ; mounted: the Runner takes it
    ld b,MOUNTED_DAMAGE
    ld a,(rn_hits)
    inc a
    ld (rn_hits),a
    cp RUNNER_HITS
    jr c,.energy
    ; the Runner is killed and the rider thrown off
    xor a
    ld (rn_hits),a
    ld (pl_speed),a
    ld (pl_jump),a
    ld (scroll_dir),a
    ld a,RUNNER_ABSENT
    ld (rn_state),a
    ld hl,(pl_x)
    ld de,RIDER_ON_RUNNER
    add hl,de
    ld a,h
    and #1F
    ld h,a
    ld (pl_x),hl
.unplug:
    ld a,MODE_FOOT
    ld (pl_mode),a
.energy:
    ld a,(pl_energy)
    sub b
    jr nc,.left
    xor a
.left:
    ld (pl_energy),a
    or a
    ret nz
    ld a,1
    ld (game_over),a
    ret

; ---------------------------------------------------------------------------
; Sprites and HUD.

; Add the enemies and missiles in or near the view to the sprite list.
enemy_sprites:
    ld hl,(scroll_pos)
    add hl,hl
    add hl,hl
    ld (.view+1),hl
    ld (.view2+1),hl
    ld ix,enemies
    ld b,MAX_ENEMIES
.enemy:
    ld a,(ix+0)
    or a
    jr z,.next
    push bc
    TYPE_ENTRY
    ; on screen: -width < x - view < 160
    ld l,(ix+1)
    ld h,(ix+2)
    ld de,16
    add hl,de
.view:
    ld de,0
    or a
    sbc hl,de
    ld a,h
    and 3
    jr nz,.hidden
    ld a,l
    cp 160+16
    jr nc,.hidden
    ; frame: two-frame animation every 4 ticks for those that have two
    ld a,(ix+0)
    cp E_CELL
    ld a,0
    jr z,.frame
    ld a,(en_tick)
    rrca
    rrca
    and 1
.frame:
    add a,(iy+0)
    ld l,(ix+1)
    ld h,(ix+2)
    ld c,(ix+3)
    call list_add
.hidden:
    pop bc
.next:
    ld de,EN_SIZE
    add ix,de
    djnz .enemy
    ; missiles
    ld iy,missiles
    ld b,MAX_MISSILES
.missile:
    ld a,(iy+0)
    or a
    jr z,.next_missile
    ld l,(iy+1)
    ld h,(iy+2)
    ld de,16
    add hl,de
.view2:
    ld de,0
    or a
    sbc hl,de
    ld a,h
    and 3
    jr nz,.next_missile
    ld a,l
    cp 160+16
    jr nc,.next_missile
    push bc
    ld l,(iy+3)
    ld h,(iy+4)
    srl h
    rr l
    srl h
    rr l
    ld c,l
    ld l,(iy+1)
    ld h,(iy+2)
    ld a,(iy+0)
    cp M_ROCK
    ld a,SPR_BOMB
    jr nz,.add
    ld a,SPR_ROCK
.add:
    call list_add
    pop bc
.next_missile:
    ld de,MS_SIZE
    add iy,de
    djnz .missile
    ret

; The ENERGY bar in the HUD, if it changed: 25 bytes for full; green, then
; yellow below half, red below a quarter.
ENERGY_LINE equ 35
ENERGY_BYTE equ 51
ENERGY_BYTES equ 25

energy_bar:
    ld a,(pl_energy)
    srl a
    srl a
    ld d,a                  ; bytes
    ld a,(pl_energy)
    ld e,DOT_STABLE
    ld c,0
    cp MAX_ENERGY/2+1
    jr nc,.colour
    ld e,DOT_UNSTABLE
    ld c,32
    cp MAX_ENERGY/4
    jr nc,.colour
    ld e,DOT_DRAINED
    ld c,64
.colour:
    ld a,c
    or d                    ; what is shown: bytes + 32 * colour
    ld hl,energy_shown
    cp (hl)
    ret z
    ld (hl),a
    ld hl,energy_lines
    ld c,ENERGY_BYTES
    jp draw_bar

energy_lines:
y=ENERGY_LINE
    repeat 5
    dw HUD_BASE+(y&7)*#800+(y>>3)*80+ENERGY_BYTE
    assert ((HUD_BASE+(y&7)*#800+(y>>3)*80+ENERGY_BYTE)&#FF)+ENERGY_BYTES <= 256
y=y+1
    rend

enemies:      ds MAX_ENEMIES*EN_SIZE
missiles:     ds MAX_MISSILES*MS_SIZE
pb_x:         dw 0          ; the player's hit box
pb_y:         db 0
pb_w:         db 0
pb_h:         db 0
pl_mid_x:     dw 0
pl_mid_y:     db 0
ca_x:         dw 0          ; boxes for overlap
ca_y:         db 0
ca_w:         db 0
ca_h:         db 0
cb_x:         dw 0
cb_y:         db 0
cb_w:         db 0
cb_h:         db 0
en_tick:      db 0
spawn_timer:  db 0
carrier_alive: db 0
carrier_cool: db 0
rand_seed:    dw #ACE1
pl_energy:    db 0
pl_invuln:    db 0
rn_hits:      db 0
energy_shown: db 0
score:        dw 0
game_over:    db 0
spawn_on:     db 1          ; tests turn these off / on
god_mode:     db 0
