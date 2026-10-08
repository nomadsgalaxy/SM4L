#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "pdm_hook.h"
int main(void) {
  unsigned char code[PDM_CODE_LENGTH];
  memcpy(code, pdm_install_code, sizeof code);
  assert(pdm_build_matches(PDM_IMAGE_SIZE, code));
  assert(!pdm_build_matches(PDM_IMAGE_SIZE + 0x1000, code) && !pdm_build_matches(0, code));      /* another image size */
  for (int i = 0; i < PDM_CODE_LENGTH; i++) {                                                      /* any changed byte */
    code[i] ^= 0x01;
    assert(!pdm_build_matches(PDM_IMAGE_SIZE, code));
    code[i] ^= 0x01;
  }
  assert(pdm_handle_plausible(0x10b5a) && !pdm_handle_plausible(0) && !pdm_handle_plausible(0x100000000ull) && !pdm_handle_plausible(~0ull));
  assert(pdm_action(1, 1, 1, 0x10b5a) == PDM_UNHOOK);
  assert(pdm_action(0, 1, 1, 0x10b5a) == PDM_DISABLED);          /* off-switch */
  assert(pdm_action(1, 0, 0, 0) == PDM_NOT_LOADED);              /* DLL not loaded yet: retry later */
  assert(pdm_action(1, 1, 0, 0x10b5a) == PDM_OTHER_BUILD);       /* different build: never touched */
  assert(pdm_action(1, 1, 1, 0) == PDM_NO_HOOK_YET);             /* the DLL has not installed its hook yet */
  assert(pdm_action(1, 1, 1, 0xdeadbeefcafeull) == PDM_NO_HOOK_YET);   /* implausible value: not trusted */
  assert(pdm_action(0, 0, 0, 0) == PDM_DISABLED);
  puts("PDM hook release decision checks passed");
  return 0;
}
