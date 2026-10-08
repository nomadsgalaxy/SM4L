#ifndef SM4L_PDM_HOOK_H
#define SM4L_PDM_HOOK_H
/* Facts and decision logic for releasing the 3DEXPERIENCE PLM Services connector's window-message hook, kept free of Windows
 * calls so tests/test_pdm_hook.c can check them on the host. The connector, USWC\PDMSWV6.dll, installs one WH_CALLWNDPROC
 * hook on CAD's UI thread; every message sent on that thread then calls into it, and releasing it made rebuilds about 2.6x
 * faster. The numbers below come from the DLL with SHA256 15e598890bd4cb43db80c3de3a279ccd7ed4459f8c1a7f6f5345e3e62b432389
 * (2,602,496 bytes); tests/test_pdm_hook.py checks them against that file when it is installed. Any other build is left alone. */
#define PDM_IMAGE_SIZE 0x281000u   /* SizeOfImage of that DLL */
#define PDM_CODE_RVA 0xab1d9u      /* the SetWindowsHookExW call site that stores the handle */
#define PDM_HANDLE_RVA 0x24abd0u   /* global holding the HHOOK (8 bytes) */
#define PDM_COUNT_RVA 0x24abd8u    /* reference count (4 bytes) */
#define PDM_CODE_LENGTH 36
static const unsigned char pdm_install_code[PDM_CODE_LENGTH] = {
    0xff, 0x15, 0xf1, 0xef, 0x10, 0x00, 0x44, 0x8b, 0xc8, 0x45, 0x33, 0xc0, 0x48, 0x8d, 0x15, 0xb4, 0xe2, 0xff,
    0xff, 0x41, 0x8d, 0x48, 0x04, 0xff, 0x15, 0x8a, 0xfa, 0x10, 0x00, 0x48, 0x89, 0x05, 0xd3, 0xf9, 0x19, 0x00};

enum { PDM_DISABLED = 0, PDM_NOT_LOADED = 1, PDM_OTHER_BUILD = 2, PDM_NO_HOOK_YET = 3, PDM_UNHOOK = 4 };

/* True only for the exact build: image size and the bytes at the install site. */
static inline int pdm_build_matches(unsigned size, const unsigned char *code) {
  if (size != PDM_IMAGE_SIZE)
    return 0;
  for (int i = 0; i < PDM_CODE_LENGTH; i++)
    if (code[i] != pdm_install_code[i])
      return 0;
  return 1;
}
/* A hook handle is a small user-handle value; anything else is not trusted. */
static inline int pdm_handle_plausible(unsigned long long handle) { return handle != 0 && handle < 0x100000000ull; }
/* What to do now. enabled: the off-switch file is absent. loaded: the module is in the process. build_ok: pdm_build_matches.
 * handle: the value read from the global (only used when the build matches). */
static inline int pdm_action(int enabled, int loaded, int build_ok, unsigned long long handle) {
  if (!enabled)
    return PDM_DISABLED;
  if (!loaded)
    return PDM_NOT_LOADED;
  if (!build_ok)
    return PDM_OTHER_BUILD;
  if (!pdm_handle_plausible(handle))
    return PDM_NO_HOOK_YET;
  return PDM_UNHOOK;
}
#endif
