; The player: the rider, mounted on the Runner or on foot, the Runner on its
; own, the rider's bolts, and the camera.
;
; Mounted, left/right ride with acceleration (up to 4 pixels a frame, the
; scroll speed) and the camera keeps the Runner centred; up jumps; fire
; shoots forward, fire with up shoots diagonally up. On foot the rider walks
; 1 pixel a frame, the screen does not scroll, fire shoots forward, fire
; with up shoots straight up, or diagonally with left/right too. Fire and
; down together dismount, or mount when the rider stands at the Runner.
; Whistling (W) calls the waiting Runner over, or brings a spare Runner in
; from the edge of the view if there is none. On mounting, the camera pans
; back to centre the Runner before the controls return.
;
; Positions are world x in eighths of a pixel (0-8191 around the planet),
; so speeds can be fractional. Frames facing left are the right-facing frame
; number + FACE_LEFT.

FACE_LEFT     equ SPR_MOUNTED0_L-SPR_MOUNTED0_R
VIEW_CX       equ 72        ; mounted sprite's screen x when centred
MOUNTED_Y     equ 73        ; tops of the sprites standing on the crust
RUNNER_Y      equ 75
RIDER_Y       equ 87
RIDER_ON_RUNNER equ 4*8     ; rider's x on the Runner (eighths)

ACCEL         equ 3         ; eighths of a pixel per frame, per frame
DECEL         equ 2
MAX_SPEED     equ 32        ; 4 pixels a frame
WALK_SPEED    equ 8         ; 1 pixel a frame
RUN_TO_RIDER  equ 24        ; a called Runner runs at 3 pixels a frame
MOUNT_REACH   equ 6         ; pixels between rider and Runner to mount
VIEW_MIN_X    equ 2         ; rider on foot stays on screen
VIEW_MAX_X    equ 150
FIRE_COOLDOWN equ 6         ; frames between bolts
MAX_SHOTS     equ 4
SHOT_SIZE     equ 6         ; frame (0 = free), x (pixels, 2), y, dx, dy
START_SPARES  equ 3
MAX_SPARES    equ 5

MODE_MOUNTED  equ 0
MODE_FOOT     equ 1
MODE_MOUNTING equ 2

RUNNER_RIDDEN equ 0
RUNNER_IDLE   equ 1
RUNNER_COMING equ 2
RUNNER_ABSENT equ 3         ; dead (later milestones) or never called

IN_UP    equ 0              ; joy_state bits
IN_DOWN  equ 1
IN_LEFT  equ 2
IN_RIGHT equ 3
IN_FIRE  equ 4
IN_WHISTLE equ 5

; HL (eighths of a pixel) -> HL (pixels).
macro TO_PIXELS
    srl h
    rr l
    srl h
    rr l
    srl h
    rr l
mend

; Start the player: mounted, standing, centred in the view at scroll 0.
player_init:
    ld hl,VIEW_CX*8
    ld (pl_x),hl
    xor a
    ld (pl_mode),a
    ld (pl_face),a
    ld (pl_speed),a
    ld (pl_jump),a
    ld (rn_state),a
    ld a,START_SPARES
    ld (pl_spares),a
    ret

; One frame of the player: input, movement, bolts, camera (sets scroll_dir).
player_update:
    ld a,(joy_state)
    ld c,a
    ld a,(joy_prev)
    cpl
    and c
    ld (joy_new),a          ; just pressed
    ld a,c
    ld (joy_prev),a
    ld hl,pl_cool
    ld a,(hl)
    or a
    jr z,.cooled
    dec (hl)
.cooled:
    ld a,(pl_mode)
    cp MODE_FOOT
    jp z,update_foot
    cp MODE_MOUNTING
    jp z,update_mounting

update_mounted:
    ld a,(pl_jump)
    or a
    jr nz,.no_dismount
    call fire_down
    jp nz,dismount
.no_dismount:
    ; ride: accelerate the way the stick points, skid when reversing
    ld a,(joy_state)
    ld c,a
    ld a,(pl_face)
    or a
    jr nz,.facing_left
    bit IN_RIGHT,c
    jr nz,.speed_up
    bit IN_LEFT,c
    jr nz,.reverse
    jr .slow_down
.facing_left:
    bit IN_LEFT,c
    jr nz,.speed_up
    bit IN_RIGHT,c
    jr nz,.reverse
.slow_down:
    ld a,(pl_speed)
    sub DECEL
    jr nc,.set_speed
    xor a
    jr .set_speed
.reverse:
    ld a,(pl_speed)
    sub ACCEL
    jr z,.turn
    jr nc,.set_speed
.turn:
    ld a,(pl_face)
    xor 1
    ld (pl_face),a
    xor a
    jr .set_speed
.speed_up:
    ld a,(pl_speed)
    add a,ACCEL
    cp MAX_SPEED
    jr c,.set_speed
    ld a,MAX_SPEED
.set_speed:
    ld (pl_speed),a
    ld hl,pl_x
    call move_x
    ; legs: one step per 4 pixels ridden
    ld a,(pl_speed)
    ld hl,pl_legs
    add a,(hl)
    ld (hl),a
    ; jump: up starts one (fire with up aims instead)
    ld a,(pl_jump)
    or a
    jr nz,.in_air
    ld a,(joy_new)
    bit IN_UP,a
    jr z,.shoot
    ld a,(joy_state)
    bit IN_FIRE,a
    jr nz,.shoot
.in_air:
    ld a,(pl_jump)
    inc a
    cp JUMP_FRAMES+1
    jr c,.jumping
    xor a
.jumping:
    ld (pl_jump),a
.shoot:
    call can_fire
    jr nz,.camera
    ; bolt from the lance: forward, or diagonally up with up held
    ld hl,(pl_x)
    TO_PIXELS
    call jump_offset
    neg
    add a,MOUNTED_Y+7
    ld c,a
    ld a,(joy_state)
    bit IN_UP,a
    jr nz,.diagonal
    ld de,16
    ld b,-4
    call fire_forward
    jr .camera
.diagonal:
    ld a,c
    sub 6
    ld c,a
    ld de,14
    ld b,-2
    call fire_diagonal
.camera:
    call camera_follow
    jp update_shots

; Rider on foot.
update_foot:
    call fire_down
    jr z,.no_mount
    call try_mount
    jp z,update_shots
.no_mount:
    ld a,(joy_new)
    bit IN_WHISTLE,a
    call nz,whistle
    ; walk, staying on screen
    ld a,(joy_state)
    ld c,a
    xor a
    ld (pl_walking),a
    bit IN_RIGHT,c
    jr z,.not_right
    xor a
    jr .walk
.not_right:
    bit IN_LEFT,c
    jr z,.walked
    ld a,1
.walk:
    ld (pl_face),a
    ld a,WALK_SPEED
    ld (pl_speed),a
    ld (pl_walking),a
    ld hl,pl_x
    call move_x
    call clamp_to_view
    ld hl,pl_legs
    ld a,(hl)
    add a,WALK_SPEED
    ld (hl),a
.walked:
    xor a
    ld (pl_speed),a
    ld (scroll_dir),a
    ; shoot: forward; with up, straight up or diagonally with a direction
    call can_fire
    jr nz,.runner
    ld hl,(pl_x)
    TO_PIXELS
    ld a,(joy_state)
    bit IN_UP,a
    jr nz,.up
    ld c,RIDER_Y+5
    ld de,8
    ld b,-4
    call fire_forward
    jr .runner
.up:
    ld c,RIDER_Y-4
    and (1<<IN_LEFT)|(1<<IN_RIGHT)
    jr nz,.diagonal
    ld de,4
    add hl,de
    ld a,SPR_SHOT_V
    ld de,SHOT_MOVE_U
    call add_shot
    jr .runner
.diagonal:
    ld de,6
    ld b,-2
    call fire_diagonal
.runner:
    call update_runner
    jp update_shots

; Climbing on: the camera pans to centre the Runner, then the controls return.
update_mounting:
    call camera_follow
    jr nz,.panning
    xor a                   ; MODE_MOUNTED
    ld (pl_mode),a
.panning:
    jp update_shots

; NZ if fire and down are held and one of them was just pressed.
fire_down:
    ld a,(joy_state)
    and (1<<IN_FIRE)|(1<<IN_DOWN)
    cp (1<<IN_FIRE)|(1<<IN_DOWN)
    jr nz,.no
    ld a,(joy_new)
    and (1<<IN_FIRE)|(1<<IN_DOWN)
    ret
.no:
    xor a
    ret

; Z if a bolt may be fired now: fire held, down not held, cooled down.
can_fire:
    ld a,(joy_state)
    and (1<<IN_FIRE)|(1<<IN_DOWN)
    cp 1<<IN_FIRE
    ret nz
    ld a,(pl_cool)
    or a
    ret

; Get off: the Runner waits where it stands, the rider steps down onto it.
dismount:
    ld hl,(pl_x)
    ld (rn_x),hl
    ld de,RIDER_ON_RUNNER
    add hl,de
    ld a,h
    and #1F
    ld h,a
    ld (pl_x),hl
    ld a,(pl_face)
    ld (rn_face),a
    ld a,RUNNER_IDLE
    ld (rn_state),a
    ld a,MODE_FOOT
    ld (pl_mode),a
    xor a
    ld (pl_speed),a
    ld (scroll_dir),a
    jp update_shots

; Mount if the waiting Runner is within reach: Z when mounted.
try_mount:
    ld a,(rn_state)
    cp RUNNER_IDLE
    ret nz
    ld hl,(rn_x)
    ld de,RIDER_ON_RUNNER
    add hl,de
    call distance_to_rider  ; A = |rider - Runner| pixels (capped)
    cp MOUNT_REACH+1
    jr nc,.far
    ld hl,(rn_x)
    ld (pl_x),hl
    ld a,(rn_face)
    ld (pl_face),a
    xor a
    ld (pl_speed),a
    ld (pl_jump),a
    ld (rn_state),a         ; RUNNER_RIDDEN
    ld a,MODE_MOUNTING
    ld (pl_mode),a
    xor a
    ret
.far:
    or 1
    ret

; A = |pl_x - HL| in pixels, up to 255 (positions in eighths, wrapping).
distance_to_rider:
    ex de,hl
    ld hl,(pl_x)
    or a
    sbc hl,de
    ld a,h
    and #1F
    ld h,a
    bit 4,h                 ; more than half the planet: the other way round
    jr z,.positive
    ld a,h
    or #E0
    ld h,a
    ex de,hl
    ld hl,0
    or a
    sbc hl,de
.positive:
    TO_PIXELS
    ld a,h
    or a
    ld a,l
    ret z
    ld a,255
    ret

; W: call the waiting Runner over, or bring a spare one in from the edge.
whistle:
    ld a,(rn_state)
    cp RUNNER_IDLE
    jr z,.come
    cp RUNNER_ABSENT
    ret nz
    ld a,(pl_spares)
    or a
    ret z
    dec a
    ld (pl_spares),a
    call hud_spares
    ; enter from the edge behind the rider's back
    ld hl,(scroll_pos)
    add hl,hl
    add hl,hl               ; view x in pixels
    ld a,(pl_face)
    or a
    jr nz,.from_right
    ld de,-16
    jr .enter
.from_right:
    ld de,160
.enter:
    add hl,de
    add hl,hl
    add hl,hl
    add hl,hl
    ld a,h
    and #1F
    ld h,a
    ld (rn_x),hl
.come:
    ld a,RUNNER_COMING
    ld (rn_state),a
    ret

; The Runner on its own: a called one runs to the rider and waits there.
update_runner:
    ld a,(rn_state)
    cp RUNNER_COMING
    ret nz
    ld hl,(rn_x)
    ld de,RIDER_ON_RUNNER
    add hl,de
    call distance_to_rider
    cp 3+1
    jr nc,.run
    ld a,RUNNER_IDLE
    ld (rn_state),a
    ret
.run:
    ; head for the rider: the sign of rider - Runner, the short way round
    ld de,(rn_x)
    ld hl,(pl_x)
    or a
    sbc hl,de
    bit 4,h                 ; rider - Runner, over half the planet: left
    ld a,0
    jr z,.face
    inc a
.face:
    ld (rn_face),a
    ld a,RUN_TO_RIDER
    ld (rn_speed),a
    ld hl,rn_legs
    add a,(hl)
    ld (hl),a
    ld hl,rn_x
    ld a,(rn_face)
    ld b,a
    ld a,RUN_TO_RIDER
    jp move_x_dir

; Move the position at HL by pl_speed eighths, the way pl_face points.
move_x:
    ld a,(pl_face)
    ld b,a
    ld a,(pl_speed)
; Move the position at HL by A eighths, left if B is non-zero.
move_x_dir:
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld c,a
    ld a,b
    or a
    ld b,0
    jr z,.add
    or a
    sbc hl,bc
    jr .store
.add:
    add hl,bc
.store:
    ld a,h
    and #1F
    ex de,hl
    ld (hl),a
    dec hl
    ld (hl),e
    ret

; Keep the rider on foot inside the view.
clamp_to_view:
    ld hl,(scroll_pos)
    add hl,hl
    add hl,hl
    ex de,hl                ; view x, pixels
    ld hl,(pl_x)
    TO_PIXELS
    or a
    sbc hl,de
    ld a,h
    and 3
    ld h,a
    bit 1,h
    jr z,.signed
    ld a,h
    or #FC
    ld h,a
.signed:
    ; HL = screen x, signed
    bit 7,h
    jr nz,.too_left
    ld a,h
    or a
    jr nz,.too_right
    ld a,l
    cp VIEW_MIN_X
    jr c,.too_left
    cp VIEW_MAX_X+1
    ret c
.too_right:
    ld hl,VIEW_MAX_X
    jr .set
.too_left:
    ld hl,VIEW_MIN_X
.set:
    add hl,de
    add hl,hl
    add hl,hl
    add hl,hl
    ld a,h
    and #1F
    ld h,a
    ld (pl_x),hl
    ret

; Set scroll_dir to bring the mounted sprite to the view's centre, one
; column a frame. Z when it is centred.
camera_follow:
    ld hl,(pl_x)
    TO_PIXELS
    ld de,-VIEW_CX
    add hl,de
    srl h
    rr l
    srl h
    rr l                    ; target column (mod 256)
    ld a,(scroll_pos)
    ld c,a
    ld a,l
    sub c
    jr z,.set
    ld a,1
    jp p,.set
    ld a,-1
.set:
    ld (scroll_dir),a
    or a
    ret

; A = how far up the jump has the Runner (0 on the ground).
jump_offset:
    ld a,(pl_jump)
    or a
    ret z
    push hl
    ld hl,jump_table-1
    add a,l
    ld l,a
    adc a,h
    sub l
    ld h,a
    ld a,(hl)
    pop hl
    ret

; Fire a bolt forward from pixel x HL: DE pixels ahead when facing right,
; B (negative) when facing left; C = y.
fire_forward:
    ld a,(pl_face)
    or a
    jr z,.right
    ld e,b
    ld d,#FF
    add hl,de
    ld a,SPR_SHOT_H
    ld de,SHOT_MOVE_L
    jr add_shot
.right:
    add hl,de
    ld a,SPR_SHOT_H
    ld de,SHOT_SPEED
    jr add_shot

; Fire a bolt diagonally up, the way the rider faces, or the way the stick
; points on foot: offsets as for fire_forward.
fire_diagonal:
    ld a,(pl_mode)
    cp MODE_FOOT
    ld a,(pl_face)
    jr nz,.facing
    ld a,(joy_state)
    and 1<<IN_LEFT          ; on foot: the stick decides
.facing:
    or a
    jr z,.right
    ld e,b
    ld d,#FF
    add hl,de
    ld a,SPR_SHOT_DL
    ld de,SHOT_MOVE_UL
    jr add_shot
.right:
    add hl,de
    ld a,SPR_SHOT_D
    ld de,SHOT_MOVE_UR

; Start bolt frame A at pixel x HL, y C, moving E pixels across and D down
; per frame, in a free slot (none: no bolt). Starts the cooldown.
add_shot:
    push af
    ld ix,shots
    ld b,MAX_SHOTS
.slot:
    ld a,(ix+0)
    or a
    jr z,.free
    push de
    ld de,SHOT_SIZE
    add ix,de
    pop de
    djnz .slot
    pop af
    ret
.free:
    pop af
    ld (ix+0),a
    ld a,h
    and 3
    ld (ix+2),a
    ld (ix+1),l
    ld (ix+3),c
    ld (ix+4),e
    ld (ix+5),d
    ld a,FIRE_COOLDOWN
    ld (pl_cool),a
    ret

; Bolt moves per frame, as DE for add_shot (D = dy, E = dx).
SHOT_SPEED   equ 8
SHOT_DIAG    equ 6
SHOT_MOVE_L  equ 256-SHOT_SPEED
SHOT_MOVE_U  equ (256-SHOT_SPEED)*256
SHOT_MOVE_UR equ (256-SHOT_DIAG)*256+SHOT_DIAG
SHOT_MOVE_UL equ (256-SHOT_DIAG)*256+256-SHOT_DIAG

; Move the bolts; drop those that leave the view.
update_shots:
    ld ix,shots
    ld b,MAX_SHOTS
.shot:
    ld a,(ix+0)
    or a
    jr z,.next
    ; y: gone above the top (wraps past 255) or below the playfield
    ld a,(ix+3)
    add a,(ix+5)
    ld (ix+3),a
    cp PLAY_ROWS*8-6
    jr nc,.drop
    ; x += dx (signed), within the planet
    ld a,(ix+4)
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
    ; gone off either side of the view?
    ex de,hl
    ld hl,(scroll_pos)
    add hl,hl
    add hl,hl
    ex de,hl
    or a
    sbc hl,de
    ld a,h
    and 3
    jr nz,.left
    ld a,l
    cp VIEW_BYTES*2
    jr c,.next              ; on screen
    jr .drop
.left:
    cp 3
    jr nz,.drop
    ld a,l
    cp (-8)&#FF
    jr nc,.next             ; up to 8 pixels left of the view, still showing
.drop:
    ld (ix+0),0
.next:
    ld de,SHOT_SIZE
    add ix,de
    djnz .shot
    ret

; ---------------------------------------------------------------------------
; Sprite list.

; Start this frame's list in the back buffer's list.
list_begin:
    ld ix,(back_list)
    inc ix
    xor a
    ld (list_count),a
    ret

; Append frame A at world x HL (pixels) and y C.
list_add:
    ld (ix+0),a
    ld (ix+1),l
    ld a,h
    and 3
    ld (ix+2),a
    ld (ix+3),c
    ld de,REC_SIZE
    add ix,de
    ld hl,list_count
    inc (hl)
    ret

list_end:
    ld a,(list_count)
    ld hl,(back_list)
    ld (hl),a
    ret

; Add the Runner, the rider (or both, mounted) and the bolts to the list.
player_sprites:
    ; the Runner on its own
    ld a,(rn_state)
    cp RUNNER_IDLE
    jr c,.rider
    cp RUNNER_ABSENT
    jr z,.rider
    ld b,SPR_RUNNER_STAND_R
    cp RUNNER_COMING
    jr nz,.runner_frame
    ld a,(rn_legs)
    rlca
    rlca
    rlca
    and 3                   ; a step per 4 pixels
    add a,SPR_RUNNER0_R
    ld b,a
.runner_frame:
    ld a,(rn_face)
    call facing
    ld hl,(rn_x)
    TO_PIXELS
    ld c,RUNNER_Y
    ld a,b
    call list_add
.rider:
    ld a,(pl_mode)
    cp MODE_FOOT
    jr z,.on_foot
    ; mounted: legs move with the ride, tucked in a jump
    ld a,(pl_jump)
    or a
    ld b,SPR_MOUNTED1_R
    jr nz,.mounted_frame
    ld a,(pl_legs)
    rlca
    rlca
    rlca
    and 3
    add a,SPR_MOUNTED0_R
    ld b,a
.mounted_frame:
    ld a,(pl_face)
    call facing
    push bc
    call jump_offset
    pop bc
    neg
    add a,MOUNTED_Y
    ld c,a
    ld hl,(pl_x)
    TO_PIXELS
    ld a,b
    call list_add
    jr .shots
.on_foot:
    ld b,SPR_RIDER_UP_R
    ld a,(joy_state)
    bit IN_UP,a
    jr nz,.rider_frame
    ld b,SPR_RIDER_STAND_R
    ld a,(pl_walking)
    or a
    jr z,.rider_frame
    ld a,(pl_legs)
    rlca
    rlca
    rlca
    rlca
    and 1                   ; a step per 2 pixels walked
    add a,SPR_RIDER_WALK0_R
    ld b,a
.rider_frame:
    ld a,(pl_face)
    call facing
    ld hl,(pl_x)
    TO_PIXELS
    ld c,RIDER_Y
    ld a,b
    call list_add
.shots:
    ld iy,shots
    ld b,MAX_SHOTS
.shot:
    ld a,(iy+0)
    or a
    jr z,.next
    push bc
    ld l,(iy+1)
    ld h,(iy+2)
    ld c,(iy+3)
    call list_add
    pop bc
.next:
    ld de,SHOT_SIZE
    add iy,de
    djnz .shot
    ret

; B = frame B turned to face A (0 right, else left).
facing:
    or a
    ret z
    ld a,b
    add a,FACE_LEFT
    ld b,a
    ret

; ---------------------------------------------------------------------------
; HUD: spare Runners, as icons after the RUNNERS label.

SPARES_LINE   equ 47        ; HUD lines 47-51 (see tools/gen_hud.py)
SPARES_X_BYTE equ 20        ; pixel 40, one icon every 3 bytes
ICON_FULL     equ #F0       ; pen 5 (bright green), both pixels
ICON_EMPTY    equ #0C       ; pen 2 (grey)

hud_spares:
    ld a,(pl_spares)
    ld c,a
    ld b,0                  ; icon number
.icon:
    ld a,b
    cp c
    ld a,ICON_FULL
    jr c,.draw
    ld a,ICON_EMPTY
.draw:
    push bc
    ld e,a
    ; the icon's column
    ld a,b
    add a,a
    add a,b
    add a,SPARES_X_BYTE
    ld c,a
    ld hl,spares_lines
    ld b,5
.line:
    push hl
    ld a,(hl)
    inc hl
    ld h,(hl)
    add a,c
    ld l,a
    jr nc,.same
    inc h
.same:
    ld (hl),e
    inc hl
    ld (hl),e
    pop hl
    inc hl
    inc hl
    djnz .line
    pop bc
    inc b
    ld a,b
    cp MAX_SPARES
    jr c,.icon
    ret

spares_lines:
y=SPARES_LINE
    repeat 5
    dw HUD_BASE+(y&7)*#800+(y>>3)*80
y=y+1
    rend

; ---------------------------------------------------------------------------

JUMP_FRAMES equ 16
jump_table:                 ; pixels above the ground, frame by frame
    db 5,10,14,17,20,22,23,24,24,23,22,20,17,14,10,5

pl_x:       dw 0            ; mounted sprite / rider on foot, eighths
pl_mode:    db 0
pl_face:    db 0            ; 0 right, 1 left
pl_speed:   db 0            ; eighths of a pixel per frame
pl_legs:    db 0            ; animation: eighths ridden or walked
pl_walking: db 0
pl_jump:    db 0            ; frame of the jump, 0 on the ground
pl_cool:    db 0            ; frames until the next bolt
pl_spares:  db 0
rn_x:       dw 0            ; the Runner when not ridden
rn_state:   db 0
rn_face:    db 0
rn_speed:   db 0
rn_legs:    db 0
joy_prev:   db 0
joy_new:    db 0
list_count: db 0
shots:      ds MAX_SHOTS*SHOT_SIZE
