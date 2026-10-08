#include <assert.h>
#include <stdio.h>
#include "swp_dedupe.h"
int main(void) {
  static const unsigned short good[] = {'m','s','c','t','l','s','_','p','r','o','g','r','e','s','s','3','2'};
  static const unsigned short other[] = {'m','s','c','t','l','s','_','s','t','a','t','u','s','b','a','r','3','2'};
  static const unsigned short near[] = {'m','s','c','t','l','s','_','p','r','o','g','r','e','s','s','3','3'};
  assert(swp_class_is_progress(good, 17) && !swp_class_is_progress(other, 18) && !swp_class_is_progress(near, 17));
  assert(!swp_class_is_progress(good, 16));
  const int r[4] = {0, 5, 120, 19};                       /* the status bar's progress bar: 0,5 120x14 */
  assert(swp_rect_noop(0, 5, 120, 14, 4, r));            /* same rect, NOZORDER only */
  assert(swp_rect_noop(9, 9, 120, 14, 4 | 2, r));        /* NOMOVE: position ignored */
  assert(swp_rect_noop(0, 5, 99, 99, 4 | 1, r));         /* NOSIZE: size ignored */
  assert(!swp_rect_noop(1, 5, 120, 14, 4, r) && !swp_rect_noop(0, 5, 121, 14, 4, r) && !swp_rect_noop(0, 5, 120, 15, 4, r));
  assert(!swp_rect_noop(0, 5, 120, 14, 0, r));           /* z-order change requested: not a no-op */
  assert(swp_dedupe_skip(1, 1, 4, 1, 1));
  assert(!swp_dedupe_skip(0, 1, 4, 1, 1));               /* off-switch */
  assert(!swp_dedupe_skip(1, 0, 4, 1, 1));               /* other callers are never touched */
  assert(!swp_dedupe_skip(1, 1, 4 | 0x40, 1, 1));        /* SWP_SHOWWINDOW */
  assert(!swp_dedupe_skip(1, 1, 4 | 0x20, 1, 1));        /* SWP_FRAMECHANGED */
  assert(!swp_dedupe_skip(1, 1, 4 | 0x10, 1, 1));        /* SWP_NOACTIVATE added: not exactly NOZORDER */
  assert(!swp_dedupe_skip(1, 1, 4, 0, 1) && !swp_dedupe_skip(1, 1, 4, 1, 0));
  puts("SetWindowPos dedupe decision checks passed");
  return 0;
}
