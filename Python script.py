# kicad_series_stack_chamfer_coil.py
# Series-stacked ("Flipper-style") CHAMFERED-RECTANGLE double-spiral for KiCad.
# Flat top/bottom/sides scaled to an A x B outline, with corners cut at a TRUE
# 45 degrees (equal cut in x and y -> diagonal slope is exactly +/-1).
#
# TOPOLOGY  (unchanged)
#   Top (F.Cu):    outer terminal --> spirals INWARD to centre.
#   Centre via:    F.Cu -> B.Cu at the inner junction.
#   Bottom (B.Cu): spirals BACK OUTWARD to a second outer terminal.
#   ==> SERIES, series-aiding: the 8-vertex cycle advances in ONE rotational
#   direction along the whole inward+outward path, so both layers' fields ADD
#   (guaranteed by construction). Both terminals end stacked at the outer edge.
#
# WHY 45 deg holds under stretch
#   Each turn is a rectangle (half-extents hw_i, hh_i) with each corner cut by
#   the SAME amount c_i in BOTH x and y -> the chamfer diagonal is always slope
#   +/-1 = 45 deg, regardless of the A:B aspect ratio. The cut scales with turn
#   size (c_i = CHAMFER * shorter-half-dimension) so inner turns stay valid.
#
# ***  INDUCTANCE vs a single N-turn layer  ***
#   L_total = 2*L_layer*(1 + k), k ~ 0.9-1  =>  ~3.6-4x one layer.
#   A single 60-turn layer ~= 100 uH -> this coil ~= 380 uH, cap ~16 nF -> ~4 nF.
#   MEASURE on an LCR meter and set C = 1/((2*pi*f)^2 * L). For ~100 uH TOTAL,
#   cut N per layer (~31 each) and widen traces for higher Q.
#
# HOW TO RUN
#   1. Open your 2-layer .kicad_pcb in the PCB editor.
#   2. Tools -> Scripting Console.
#   3. exec(open('/full/absolute/path/to/kicad_series_stack_chamfer_coil.py').read())
#   4. Save the board.
#
# KiCad 7 / 8 / 9. (KiCad 6: swap pcbnew.VECTOR2I -> pcbnew.wxPoint.)

import pcbnew

board = pcbnew.GetBoard()

# ---------------------------------------------------------------------------
# PARAMETERS  -- from Coil64 (rectangular winding, 100 uH @ 125 kHz)
# ---------------------------------------------------------------------------
A          = 50.0        # outer width  A (mm)
B          = 40.0        # outer height B (mm)
N          = 60          # turns PER LAYER (total effective turns ~= 2N)
W          = 0.178       # trace width W (mm)
S          = 0.297       # winding pitch = centre-to-centre radial step (mm)

CHAMFER    = 0.25        # corner cut as a fraction of the shorter half-dim per
                         # turn. 0 = square corners, ~0.4 = strongly octagonal.

ORIGIN_X   = 100.0       # coil-centre X on the board (mm)
ORIGIN_Y   = 100.0       # coil-centre Y on the board (mm)

VIA_DRILL  = 0.4         # centre-via drill (mm) - ALL current passes through it,
VIA_PAD    = 0.8         # centre-via pad   (mm)   so keep it generous.
# ---------------------------------------------------------------------------


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(ORIGIN_X + x), mm(ORIGIN_Y + y))


def chamfer_vertex(k, hwi, hhi, ci):
    """One of the 8 chamfered-rectangle vertices, CCW. Cut ci is equal in x and
    y at every corner, so each diagonal is exactly 45 degrees."""
    return [
        (hwi,        hhi - ci),   # 0 right side, top
        (hwi - ci,   hhi),        # 1 top side, right   (0->1 = 45 deg corner)
        (-hwi + ci,  hhi),        # 2 top side, left
        (-hwi,       hhi - ci),   # 3 left side, top    (2->3 = 45 deg corner)
        (-hwi,      -hhi + ci),   # 4 left side, bottom
        (-hwi + ci, -hhi),        # 5 bottom side, left (4->5 = 45 deg corner)
        (hwi - ci,  -hhi),        # 6 bottom side, right
        (hwi,       -hhi + ci),   # 7 right side, bottom(6->7 = 45 deg corner)
    ][k % 8]


def double_spiral_points():
    """Continuous inward-then-outward chamfered-rectangle double-spiral, mm from
    centre. Index 0..M = TOP (inward); M..2M = BOTTOM (outward). Returns
    (pts, M, d_max)."""
    hw, hh = A / 2.0, B / 2.0
    d0 = W / 2.0
    M = N * 8
    d_max = d0 + S * N
    pts = []
    for i in range(2 * M + 1):
        turns = i / 8.0
        if i <= M:                       # inward: inset grows
            ins = d0 + S * turns
        else:                            # outward: inset shrinks back
            ins = d0 + S * (2 * N - turns)
        hwi = hw - ins
        hhi = hh - ins
        ci = CHAMFER * min(hwi, hhi)
        if ci < 0:
            ci = 0.0
        pts.append(chamfer_vertex(i, hwi, hhi, ci))
    return pts, M, d_max


def draw_run(pts, i0, i1, layer):
    for i in range(i0, i1):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pt(*pts[i]))
        t.SetEnd(pt(*pts[i + 1]))
        t.SetWidth(mm(W))
        t.SetLayer(layer)
        board.Add(t)


def add_center_via(xy):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(*xy))
    v.SetDrill(mm(VIA_DRILL))
    v.SetWidth(mm(VIA_PAD))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)


def main():
    pts, M, d_max = double_spiral_points()

    hw, hh = A / 2.0, B / 2.0
    gap = S - W
    inner_clear = min(hw, hh) - d_max
    print("Series-stacked chamfered rectangle (45deg corners): %d turns/layer "
          "(~%d effective)  W=%.3f  S=%.3f" % (N, 2 * N, W, S))
    print("  outer %.0fx%.0f mm  chamfer=%.2f  flat-gap=%.3fmm  inner clear=%.2fmm"
          % (A, B, CHAMFER, gap, inner_clear))
    if gap < 0.09:
        print("  !! WARNING: flat-side gap %.3fmm (~%.1f mil) below typical fab "
              "min (~0.09mm/3.5mil). Increase S or reduce W."
              % (gap, gap / 0.0254))
    if inner_clear <= 0:
        print("  !! WARNING: turns run past centre (inner clearance <= 0). "
              "Reduce N or enlarge the coil.")

    draw_run(pts, 0, M, pcbnew.F_Cu)             # top: outer -> centre
    add_center_via(pts[M])                        # F.Cu -> B.Cu junction
    draw_run(pts, M, 2 * M, pcbnew.B_Cu)          # bottom: centre -> outer

    pcbnew.Refresh()
    print("  Terminal 1 (F.Cu, outer) @ (%.3f, %.3f) mm" % pts[0])
    print("  Terminal 2 (B.Cu, outer) @ (%.3f, %.3f) mm" % pts[2 * M])
    print("  Centre via @ (%.3f, %.3f) mm" % pts[M])
    print("  Both terminals stacked at the outer edge. MEASURE L and retune C.")
    print("Done. Save the board.")


main()