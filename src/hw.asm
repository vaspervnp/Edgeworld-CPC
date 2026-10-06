; Hardware constants for the CPC 6128.

GA_PORT     equ #7F         ; gate array (B register)
CRTC_SEL    equ #BC         ; CRTC register select
CRTC_DATA   equ #BD         ; CRTC register data
PPI_A       equ #F4
PPI_B       equ #F5
PPI_C       equ #F6
PPI_CTRL    equ #F7

; Gate array RMR: mode 0, upper and lower ROM off.
RMR_MODE0_NOROM equ %10001100

; Keyboard matrix lines and bits (active low).
KB_LINE_CURSOR1 equ 0       ; bit0 up, bit1 right, bit2 down
KB_LINE_CURSOR2 equ 1       ; bit0 left
KB_LINE_SPACE   equ 5       ; bit7 space
KB_LINE_JOY0    equ 9       ; bit0 up, 1 down, 2 left, 3 right, 4 fire1, 5 fire2
