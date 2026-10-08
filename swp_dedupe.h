#ifndef SM4L_SWP_DEDUPE_H
#define SM4L_SWP_DEDUPE_H
/* Decision logic of the SetWindowPos dedupe in spacemouse-view.c, kept free of Windows calls so test_swp_dedupe.c can
 * check it on the host. SOLIDWORKS's rebuild repositions the status bar's progress bar about 120 times per rebuild to
 * the rectangle it already has; skipping exactly those calls made rebuilds about 24% faster. */

/* True when name (n UTF-16 units, no terminator needed) is "msctls_progress32". */
static inline int swp_class_is_progress(const unsigned short *name, int n) {
  static const char want[] = "msctls_progress32";
  if (n != (int)sizeof want - 1)
    return 0;
  for (int i = 0; i < n; i++)
    if (name[i] != (unsigned short)want[i])
      return 0;
  return 1;
}
/* True when the call would change nothing: same size and position as now (r = left, top, right, bottom in the
 * window's own coordinate space) and no z-order change requested. flags: SWP_NOSIZE 1, SWP_NOMOVE 2, SWP_NOZORDER 4. */
static inline int swp_rect_noop(int x, int y, int cx, int cy, unsigned flags, const int r[4]) {
  int same_size = (flags & 1) || (cx == r[2] - r[0] && cy == r[3] - r[1]);
  int same_pos = (flags & 2) || (x == r[0] && y == r[1]);
  return same_size && same_pos && (flags & 4);
}
/* Skip the call only for: enabled, caller in the known vendor routine, flags exactly SWP_NOZORDER (no show/hide,
 * frame change, activation), a progress bar, and a no-op rectangle. */
static inline int swp_dedupe_skip(int enabled, int caller_ok, unsigned flags, int is_progress, int noop) {
  return enabled && caller_ok && flags == 4 && is_progress && noop;
}
#endif
