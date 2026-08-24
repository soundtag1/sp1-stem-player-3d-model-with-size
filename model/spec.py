"""
Dimensional specification for the Teenage Engineering / Kanye West
Prototype SP-1 Stem Player  (YZY0020SP01Y4KNGK17, FCC-ID WAP3027).

Every number below is in millimetres and was derived photogrammetrically
from the reference photographs in ../photos - see ../DIMENSIONS.md for the
derivation and error bars.

Coordinate system (right handed, millimetres, origin at the body centre):

    +X  ->  along the long axis, towards the connector end
    +Y  ->  along the short axis, towards the cap / top-edge keys
    +Z  ->  out of the front (slider) face

So the front face lies at Z = +T/2 and the back plate at Z = -T/2.
"""

# --------------------------------------------------------------------------
# overall body
# --------------------------------------------------------------------------
L = 64.0          # long axis  (X)
W = 47.0          # short axis (Y)
T = 9.4           # thickness  (Z)

R_CORNER = 2.6    # corner radius of the XY outline
R_EDGE = 0.9      # fillet where the front/back faces roll into the sides

X0, X1 = -L / 2, L / 2
Y0, Y1 = -W / 2, W / 2
Z0, Z1 = -T / 2, T / 2

# --------------------------------------------------------------------------
# cap / end piece  (the strip along the +Y edge carrying the red index mark)
# --------------------------------------------------------------------------
CAP_H = 8.87                 # height of the cap strip measured from the +Y edge
SEAM_Y = Y1 - CAP_H          # = +14.63, the cap/body parting line
SEAM_W = 0.28                # visible width of the parting groove
SEAM_D = 0.16                # depth of the parting groove

# --------------------------------------------------------------------------
# front face - four control rows
# --------------------------------------------------------------------------
# Rows are centred in the main panel (below the cap) with 5.67 mm margins.
ROW_PITCH = 8.93
ROW_Y = (8.96, 0.03, -8.90, -17.83)

# ---- sliders -------------------------------------------------------------
SL_X0, SL_X1 = -6.40, 6.50   # stadium pocket extent along X
SL_H = 2.70                  # pocket height along Y
SL_DEPTH = 0.42              # pocket floor below the panel surface

SL_TRACK_X0, SL_TRACK_X1 = -5.70, 6.00
SL_TRACK_H = 1.50            # the dark slot inside the pocket
SL_TRACK_DEPTH = 0.95

KNOB_X = -4.95               # knobs are parked at the left end of travel
KNOB_D = 2.45                # knob diameter
KNOB_RISE = 0.34             # how far the knob crown stands above the panel
KNOB_CROWN = 0.18            # dome height of the crown

# ---- indicator LEDs ------------------------------------------------------
LED_X = 12.70
LED_D = 0.80
LED_DEPTH = 0.38

# ---- buttons -------------------------------------------------------------
BT_X0, BT_X1 = 17.18, 23.73  # 6.55 mm wide keys
BT_H = 2.70
BT_R = 0.45                  # corner radius of the key
BT_POCKET_DEPTH = 0.46
BT_GAP = 0.17                # gap between key edge and pocket wall
BT_KEY_RISE = 0.10           # key crown above the panel surface

# ---- cap graphics --------------------------------------------------------
TRI_CX, TRI_CY = -20.29, 18.80   # red index triangle, points -X
TRI_W, TRI_H = 2.05, 2.20
CAP_DOT_X = (19.73, 21.30)       # two small blind holes
CAP_DOT_Y = 18.80
CAP_DOT_D = 0.92
CAP_DOT_DEPTH = 0.34

# --------------------------------------------------------------------------
# +Y long edge - two keys, mic port and status LEDs
# --------------------------------------------------------------------------
TOPKEY_X = (-20.09, 20.09)   # centres
TOPKEY_LEN = 10.90           # along X
TOPKEY_WID = 5.60            # along Z
TOPKEY_R = 0.55
TOPKEY_POCKET_MARGIN = 0.70  # pocket is this much larger all round
TOPKEY_POCKET_DEPTH = 0.50
TOPKEY_RISE = 1.72           # crown above the +Y face

MIC_X = -5.20                # microphone pinhole
MIC_D = 0.90
MIC_DEPTH = 1.20
AUX_HOLE_X = -2.10           # second, smaller pinhole
AUX_HOLE_D = 0.55
AUX_HOLE_DEPTH = 0.90

STATUS_LED_X = (0.20, 2.00, 3.80, 5.60)
STATUS_LED_D = 0.70
STATUS_LED_DEPTH = 0.30

# --------------------------------------------------------------------------
# +X short end - connectors (2x 3.5 mm jack, USB-C)
# --------------------------------------------------------------------------
JACK_Y = (13.40, 0.00)       # two 3.5 mm TRS jacks
JACK_D = 4.20
JACK_DEPTH = 2.60

USBC_Y = -13.40
USBC_LEN = 8.90              # along Y
USBC_WID = 3.20              # along Z
USBC_R = 1.55
USBC_DEPTH = 2.40

# --------------------------------------------------------------------------
# -X short end - speaker grille and two round keys
# --------------------------------------------------------------------------
GRILLE_ROW_Y = (10.12, 8.00, 5.89, 3.77, 1.66)
GRILLE_COL_Z = (-0.725, 0.725)
GRILLE_D = 0.85
GRILLE_DEPTH = 1.40

ROUNDKEY_Y = (-7.53, -16.91)
ROUNDKEY_D = 4.90
ROUNDKEY_POCKET_D = 5.24
ROUNDKEY_POCKET_DEPTH = 0.38
ROUNDKEY_RISE = 0.06

# --------------------------------------------------------------------------
# back plate
# --------------------------------------------------------------------------
SCREW_POS = ((-29.00, 11.73), (29.00, -21.00))   # diagonally opposed
SCREW_D = 3.00
SCREW_DEPTH = 0.50
SCREW_HEAD_D = 2.55

# --------------------------------------------------------------------------
# appearance
# --------------------------------------------------------------------------
COL_ALU = (232, 230, 224)        # bead-blasted anodised aluminium
COL_ALU_DARK = (206, 203, 196)   # pocket floors / shaded recesses
COL_PLASTIC = (238, 236, 230)    # key and knob caps
COL_SLOT = (26, 27, 26)          # dark slot interiors
COL_CHROME = (196, 196, 192)     # the steel channel inside a slider pocket
COL_RED = (214, 52, 62)          # index triangle
COL_ETCH = (58, 58, 56)          # laser etched marks on the back
