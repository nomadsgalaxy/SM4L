typedef unsigned short W;
typedef int H;
typedef unsigned U;
typedef void *P;
typedef struct {
  U a;
  unsigned short b, c;
  unsigned char d[8];
} GUID;
typedef struct {
  unsigned short vt, r1, r2, r3;
  union {
    double dbl;
    P ptr;
    int num;
    struct {
      P a, b;
    } record;
  } val;
} VAR;
typedef struct {
  VAR *args;
  int *named;
  U count, ncount;
} DP;
typedef struct V {
  H (*query)(P, const GUID *, P *);
  U (*add)(P);
  U (*release)(P);
  H (*tic)(P, U *);
  H (*ti)(P, U, U, P *);
  H (*names)(P, const GUID *, const W **, U, U, int *);
  H (*invoke)(P, int, const GUID *, U, unsigned short, DP *, VAR *, P, U *);
} V;
typedef struct {
  V *v;
} OBJ;
__declspec(dllimport) H CoInitializeEx(P, U);
__declspec(dllimport) H CLSIDFromProgID(const W *, GUID *);
__declspec(dllimport) H GetActiveObject(const GUID *, P, P *);
__declspec(dllimport) H VariantClear(VAR *);
__declspec(dllimport) void CoUninitialize(void);
__declspec(dllimport) P GetStdHandle(U);
__declspec(dllimport) int WriteFile(P, const void *, U, U *, P);
__declspec(dllimport) void ExitProcess(U);
static P output_handle;
static P output(void) {
  return output_handle ? output_handle : GetStdHandle((U)-11);
}
static const GUID nil = {0},
                  iid = {0x00020400, 0, 0, {0xc0, 0, 0, 0, 0, 0, 0, 0x46}};
static void report(H h) {
  char line[] = "HRESULT 0x00000000\r\n";
  char hex[] = "0123456789abcdef";
  for (U i = 0; i < 8; i++)
    line[10 + i] = hex[((U)h >> (28 - 4 * i)) & 15];
  U n;
  WriteFile(output(), line, sizeof(line) - 1, &n, 0);
}
static H invoke(OBJ *o, const W *name, unsigned short flags, VAR *args, U count,
                VAR *out) {
  /* These literal names belong to fixed app/view interfaces in this helper.
   * Resolve each once rather than adding a COM round-trip to every frame. */
  static struct {
    const W *name;
    int id;
  } bindings[32];
  static U used;
  U slot = 0;
  while (slot < used && bindings[slot].name != name)
    slot++;
  int id;
  if (slot < used)
    id = bindings[slot].id;
  else {
    H h = o->v->names(o, &nil, &name, 1, 0x409, &id);
    if (h < 0)
      return h;
    if (used < 32) {
      bindings[used].name = name;
      bindings[used++].id = id;
    }
  }
  int put = -3;
  DP p = {args, flags == 4 ? &put : 0, count, flags == 4 ? 1u : 0u};
  return o->v->invoke(o, id, &nil, 0x409, flags, &p, out, 0, 0);
}

/* Only view navigation: no model edits, document creation, or saved
 * credentials. */
typedef unsigned long long Q;
typedef struct {
  U magic, seq;
  Q time;
  double v[6];
} Packet;
_Static_assert(sizeof(VAR) == 24, "Win64 VARIANT layout");
_Static_assert(sizeof(Packet) == 64, "Python packet layout");
int _fltused = 0;
__declspec(dllimport) P CreateFileW(const W *, U, U, P, U, U, P);
__declspec(dllimport) int ReadFile(P, P, U, U *, P);
__declspec(dllimport) U GetFileSize(P, U *);
__declspec(dllimport) int CloseHandle(P);
__declspec(dllimport) void GetSystemTimeAsFileTime(Q *);
__declspec(dllimport) P GetForegroundWindow(void);
__declspec(dllimport) U GetWindowThreadProcessId(P, U *);
__declspec(dllimport) void Sleep(U);
__declspec(dllimport) Q GetTickCount64(void);
__declspec(dllimport) P OpenProcess(U, int, U);
__declspec(dllimport) U WaitForSingleObject(P, U);
__declspec(dllimport) W *GetCommandLineW(void);
static H call(OBJ *o, const W *n, unsigned short f, VAR *out) {
  return invoke(o, n, f, 0, 0, out);
}
static void say(const char *s) {
  U n = 0, w;
  while (s[n])
    n++;
  WriteFile(output(), s, n, &w, 0);
}
static int option(const W *s) {
  W *c = GetCommandLineW();
  for (; *c; c++) {
    U i = 0;
    while (s[i] && c[i] == s[i])
      i++;
    if (!s[i])
      return 1;
  }
  return 0;
}
static H move(OBJ *view, const W *name, double a, double b, U count) {
  VAR args[2] = {{0}, {0}}, result = {0};
  args[0].vt = 5;
  args[0].val.dbl = count == 2 ? b : a;
  args[1].vt = 5;
  args[1].val.dbl = a;
  H h = invoke(view, name, 1, args, count, &result);
  VariantClear(&result);
  return h;
}
static H view_of(OBJ *app, VAR *doc, VAR *view) {
  H h = call(app, L"ActiveDoc", 2, doc);
  if (h < 0)
    return h;
  if (doc->vt != 9 || !doc->val.ptr)
    return (H)0x80040005;
  h = call(doc->val.ptr, L"ActiveView", 2, view);
  if (h == 0 && (view->vt != 9 || !view->val.ptr))
    return (H)0x80040005;
  return h;
}
__declspec(dllimport) U GetCurrentProcessId(void);
__declspec(dllimport) P GetActiveWindow(void);
static int focus_reason; /* 0 none, 1 foreground pid, 2 active window */
static int focused(U pid) {
  U current = 0;
  GetWindowThreadProcessId(GetForegroundWindow(), &current);
  /* Wine can report a NULL or foreign foreground while CAD has X focus;
   * an active window on the calling (UI) thread still means CAD is ours. */
  focus_reason = current == pid || current == GetCurrentProcessId() ? 1
                 : GetActiveWindow()                                ? 2
                                                                    : 0;
  return focus_reason != 0;
}
static int read_packet(Packet *p) {
  P f = CreateFileW(L"C:\\sm4l-spacemouse.bin", 0x80000000, 7, 0, 3, 0x80, 0);
  if (f == (P)-1)
    return 0;
  U n = 0;
  int ok = GetFileSize(f, 0) == sizeof(*p) &&
           ReadFile(f, p, sizeof(*p), &n, 0) && n == sizeof(*p);
  CloseHandle(f);
  if (!ok || p->magic != 0x534d344c)
    return 0;
  Q now;
  GetSystemTimeAsFileTime(&now);
  if (p->time > now || now - p->time > 2000000)
    return 0;
  for (U i = 0; i < 6; i++) {
    double limit = i < 2 ? .05 : i == 2 ? 1.2 : .1;
    if (!(p->v[i] >= -limit && p->v[i] <= limit))
      return 0;
  }
  return p->v[2] >= .8;
}
static void milliseconds(Q value) {
  char text[24];
  U n = 0, w;
  do {
    text[n++] = '0' + value % 10;
    value /= 10;
  } while (value);
  for (U i = 0; i < n / 2; i++) {
    char c = text[i];
    text[i] = text[n - 1 - i];
    text[n - 1 - i] = c;
  }
  text[n++] = '\r';
  text[n++] = '\n';
  WriteFile(output(), text, n, &w, 0);
}
static H apply(OBJ *v, OBJ *doc, const Packet *p) {
  VAR enabled = {0}, off = {0};
  H h = call(v, L"EnableGraphicsUpdate", 2, &enabled);
  if (h < 0 || enabled.vt != 11)
    return h < 0 ? h : (H)0x8000ffff;
  if (!enabled.val.num)
    return 1;
  off.vt = 11;
  off.val.num = 0;
  h = invoke(v, L"EnableGraphicsUpdate", 4, &off, 1, 0);
  if (h < 0)
    return h;
  if (p->v[0] || p->v[1])
    h = move(v, L"TranslateBy", p->v[0], p->v[1], 2);
  if (h >= 0 && p->v[2] != 1)
    h = move(v, L"ZoomByFactor", p->v[2], 0, 1);
  if (h >= 0 && (p->v[3] || p->v[4]))
    h = move(v, L"RotateAboutCenter", p->v[3], p->v[4], 2);
  if (h >= 0 && p->v[5])
    h = move(v, L"RollBy", p->v[5], 0, 1);
  H restore = invoke(v, L"EnableGraphicsUpdate", 4, &enabled, 1, 0);
  VariantClear(&enabled);
  if (restore < 0)
    return restore;
  if (h < 0)
    return h;
  VAR redraw = {0};
  h = call(doc, L"GraphicsRedraw2", 1, &redraw);
  VariantClear(&redraw);
  return h;
}
static U check(OBJ *app) {
  VAR doc = {0}, view = {0}, before = {0}, after = {0};
  H h = view_of(app, &doc, &view);
  if (h < 0) {
    say("Open a part before checking view navigation.\r\n");
    report(h);
    return 5;
  }
  OBJ *v = view.val.ptr;
  h = call(v, L"Scale2", 2, &before);
  if (h < 0 || before.vt != 5) {
    report(h);
    return 6;
  }
  Packet zoom = {0};
  zoom.v[2] = 1.01;
  h = apply(v, doc.val.ptr, &zoom);
  report(h);
  H read = call(v, L"Scale2", 2, &after);
  int changed = read == 0 && after.vt == 5 && after.val.dbl > before.val.dbl;
  H restore = invoke(v, L"Scale2", 4, &before, 1, 0);
  report(restore);
  if (!changed || h < 0 || restore < 0) {
    say("Zoom/readback/restore failed.\r\n");
    return 7;
  }
  h = move(v, L"TranslateBy", .0001, 0, 2);
  report(h);
  H undo = move(v, L"TranslateBy", -.0001, 0, 2);
  report(undo);
  if (h < 0 || undo < 0)
    return 8;
  h = move(v, L"RotateAboutCenter", .01, 0, 2);
  report(h);
  undo = move(v, L"RotateAboutCenter", -.01, 0, 2);
  report(undo);
  if (h < 0 || undo < 0)
    return 9;
  h = move(v, L"RotateAboutCenter", 0, .01, 2);
  report(h);
  undo = move(v, L"RotateAboutCenter", 0, -.01, 2);
  report(undo);
  if (h < 0 || undo < 0)
    return 9;
  h = move(v, L"RollBy", .01, 0, 1);
  report(h);
  undo = move(v, L"RollBy", -.01, 0, 1);
  report(undo);
  if (h < 0 || undo < 0)
    return 10;
  VariantClear(&before);
  VariantClear(&after);
  VariantClear(&view);
  VariantClear(&doc);
  say("Pan, zoom, pitch, yaw and roll calls passed; zoom readback changed and "
      "was restored.\r\n");
  return 0;
}
#ifndef SM4L_ADDIN
__declspec(dllimport) H SafeArrayGetLBound(P, U, int *);
__declspec(dllimport) H SafeArrayGetUBound(P, U, int *);
__declspec(dllimport) H SafeArrayAccessData(P, P *);
__declspec(dllimport) H SafeArrayUnaccessData(P);
static int benchmark(OBJ *app) {
  VAR doc = {0}, view = {0}, result = {0}, manager = {0}, stats = {0},
      names = {0}, times = {0};
  H h = view_of(app, &doc, &view);
  if (h < 0) {
    report(h);
    return 1;
  }
  Q start = GetTickCount64();
  h = call(doc.val.ptr, L"GraphicsRedraw2", 1, &result);
  say("Redraw ms: ");
  milliseconds(GetTickCount64() - start);
  report(h);
  VariantClear(&result);
  VAR top = {0};
  top.vt = 11;
  top.val.num = -1;
  start = GetTickCount64();
  h = invoke(doc.val.ptr, L"ForceRebuild3", 1, &top, 1, &result);
  say("Full rebuild ms: ");
  milliseconds(GetTickCount64() - start);
  report(h);
  if (h < 0 || result.vt != 11 || !result.val.num) {
    if (h >= 0)
      h = (H)0x80004005;
    goto done;
  }
  VariantClear(&result);
  h = call(doc.val.ptr, L"FeatureManager", 2, &manager);
  if (h < 0 || manager.vt != 9)
    goto done;
  h = call(manager.val.ptr, L"FeatureStatistics", 2, &stats);
  if (h < 0 || stats.vt != 9)
    goto done;
  h = call(stats.val.ptr, L"Refresh", 1, &result);
  if (h < 0)
    goto done;
  VariantClear(&result);
  h = call(stats.val.ptr, L"FeatureNames", 2, &names);
  if (h < 0)
    goto done;
  h = call(stats.val.ptr, L"FeatureUpdateTimes", 2, &times);
  if (h < 0)
    goto done;
  int nl, nh, tl, th;
  P nd = 0, td = 0;
  if (names.vt != 0x2008 || times.vt != 0x2005 ||
      SafeArrayGetLBound(names.val.ptr, 1, &nl) < 0 ||
      SafeArrayGetUBound(names.val.ptr, 1, &nh) < 0 ||
      SafeArrayGetLBound(times.val.ptr, 1, &tl) < 0 ||
      SafeArrayGetUBound(times.val.ptr, 1, &th) < 0 || nh < nl || th < tl ||
      nh - nl != th - tl || nh - nl > 10000) {
    h = (H)0x80070057;
    goto done;
  }
  h = SafeArrayAccessData(names.val.ptr, &nd);
  if (h < 0)
    goto done;
  h = SafeArrayAccessData(times.val.ptr, &td);
  if (h >= 0) {
    for (int i = 0; i <= nh - nl; i++) {
      W *name = ((W **)nd)[i];
      char text[256];
      U n = 0;
      while (name && name[n] && n < 255) {
        text[n] = name[n] < 128 ? (char)name[n] : '?';
        n++;
      }
      text[n] = 0;
      double seconds = ((double *)td)[i];
      if (!(seconds >= 0 && seconds < 86400)) {
        h = (H)0x80070057;
        break;
      }
      say(text);
      say(" feature ms: ");
      milliseconds((Q)(seconds * 1000));
    }
    SafeArrayUnaccessData(times.val.ptr);
  }
  SafeArrayUnaccessData(names.val.ptr);
done:
  if (h < 0)
    report(h);
  VariantClear(&times);
  VariantClear(&names);
  VariantClear(&stats);
  VariantClear(&manager);
  VariantClear(&result);
  VariantClear(&view);
  VariantClear(&doc);
  return h < 0 ? 1 : 0;
}
__declspec(dllimport) W *SysAllocString(const W *);
void entry(void) {
  GUID cls;
  OBJ *u = 0, *app = 0;
  VAR pid = {0};
  H h = CoInitializeEx(0, 2);
  if (h < 0)
    ExitProcess(1);
  h = CLSIDFromProgID(L"SldWorks.Application", &cls);
  if (h < 0)
    ExitProcess(2);
  for (U attempt = 0;; attempt++) {
    h = GetActiveObject(&cls, 0, (P *)&u);
    if (h >= 0 || (option(L"--check-view") || option(L"--benchmark")) ||
        h != (H)0x800401e3 || attempt == 899)
      break;
    if (!attempt)
      say("Waiting for SOLIDWORKS to start.\r\n");
    Sleep(1000);
  }
  if (h < 0) {
    say("SOLIDWORKS is not running.\r\n");
    report(h);
    ExitProcess(3);
  }
  h = u->v->query(u, &iid, (P *)&app);
  u->v->release(u);
  if (h < 0)
    ExitProcess(4);
  h = call(app, L"GetProcessID", 1, &pid);
  if (h < 0 || pid.vt != 3 || pid.val.num <= 0)
    ExitProcess(4);
  if (option(L"--check-view"))
    ExitProcess(check(app));
  if (option(L"--benchmark"))
    ExitProcess(benchmark(app));
  P process = OpenProcess(0x101000, 0, (U)pid.val.num);
  if (!process) {
    say("Cannot watch the CAD process.\r\n");
    ExitProcess(4);
  }
  if (option(L"--load-addin") || option(L"--unload-addin") ||
      option(L"--load-ui-addin")) {
    VAR file = {0}, result = {0};
    file.vt = 8;
    file.val.ptr = SysAllocString(option(L"--load-ui-addin")
                                      ? L"C:\\sm4l-ui-compat-v2.dll"
                                      : L"C:\\sm4l-spacemouse-v3.dll");
    if (!file.val.ptr)
      ExitProcess(5);
    h = invoke(app, option(L"--unload-addin") ? L"UnloadAddIn" : L"LoadAddIn",
               1, &file, 1, &result);
    VariantClear(&file);
    if (option(L"--unload-addin")) {
      report(h);
      report(result.val.num);
      ExitProcess(h < 0 ? 5 : 0);
    }
    say("LoadAddIn HRESULT: ");
    report(h);
    say("LoadAddIn status: ");
    report(result.val.num);
    if (h < 0 || result.vt != 3 || (result.val.num != 0 && result.val.num != 2))
      ExitProcess(5);
    VariantClear(&result);
    say("In-process SM4L add-in loaded.\r\n");
    while (WaitForSingleObject(process, 500) == 0x102) {
    }
    CloseHandle(process);
    app->v->release(app);
    CoUninitialize();
    ExitProcess(0);
  }
  say("SpaceMouse view bridge attached; open a part and focus SOLIDWORKS.\r\n");
  U last = 0, applied = 0;
  H previous_error = 0;
  Q total_ms = 0;
  U measured = 0;
  for (;;) {
    Packet p;
    Sleep(16);
    if (WaitForSingleObject(process, 0) != 0x102)
      break;
    if (!read_packet(&p) || p.seq == last)
      continue;
    last = p.seq;
    if (!focused((U)pid.val.num))
      continue;
    Q start = GetTickCount64();
    VAR doc = {0}, view = {0};
    h = view_of(app, &doc, &view);
    if (h >= 0 && focused((U)pid.val.num))
      h = apply(view.val.ptr, doc.val.ptr, &p);
    VariantClear(&view);
    VariantClear(&doc);
    total_ms += GetTickCount64() - start;
    if (++measured == 120) {
      say("Average COM view frame (ms): ");
      milliseconds(total_ms / measured);
      total_ms = 0;
      measured = 0;
    }
    if (h >= 0) {
      previous_error = 0;
      if (!applied++)
        say("SpaceMouse motion applied to the active view.\r\n");
    } else if (h != (H)0x80040005) {
      if (h != previous_error) {
        report(h);
        previous_error = h;
      }
      if (h == (H)0x80010108 || h == (H)0x800706ba)
        break;
    }
  }
  CloseHandle(process);
  app->v->release(app);
  CoUninitialize();
  ExitProcess(0);
}

#else
/* ISwAddin's IUnknown-based ABI was checked against the installed
 * swpublished.tlb. */
static const GUID addin_iid = {
    0xda306a0d,
    0xeac5,
    0x4406,
    {0x86, 0x10, 0xb1, 0xda, 0x80, 0x5d, 0x92, 0x70}};
#ifdef SM4L_UI_ADDIN
static const GUID clsid = {0xbb75177c,
                           0x6799,
                           0x4f57,
                           {0x9b, 0x75, 0x10, 0x93, 0x1d, 0x64, 0x21, 0xfa}};
#else
static const GUID clsid = {0xbb75177c,
                           0x6799,
                           0x4f57,
                           {0x9b, 0x75, 0x10, 0x93, 0x1d, 0x64, 0x21, 0xf6}};
#endif
static const GUID unknown_iid = {0, 0, 0, {0xc0, 0, 0, 0, 0, 0, 0, 0x46}};
static const GUID factory_iid = {1, 0, 0, {0xc0, 0, 0, 0, 0, 0, 0, 0x46}};
typedef struct AV {
  H (*query)(P, const GUID *, P *);
  U (*add)(P);
  U (*release)(P);
  H (*connect)(P, OBJ *, int, short *);
  H (*disconnect)(P, short *);
} AV;
typedef struct FV {
  H (*query)(P, const GUID *, P *);
  U (*add)(P);
  U (*release)(P);
  H (*create)(P, P, const GUID *, P *);
  H (*lock)(P, int);
} FV;
static OBJ *cad;
static Q timer;
static P timer_window;
static U cad_pid;
#ifndef SM4L_UI_ADDIN
static U last_sequence;
#endif
static int busy;
__declspec(dllimport) Q SetTimer(P, Q, U, void (*)(P, U, Q, U));
__declspec(dllimport) int KillTimer(P, Q);
__declspec(dllimport) int EnumWindows(int (*)(P, Q), Q);
__declspec(dllimport) int IsWindowVisible(P);
__declspec(dllimport) int IsWindowEnabled(P);
__declspec(dllimport) P GetWindow(P, U);
__declspec(dllimport) int GetWindowRect(P, int *);
__declspec(dllimport) U GetCurrentThreadId(void);
static int pick_window(P window, Q ignored) {
  (void)ignored;
  U pid = 0;
  GetWindowThreadProcessId(window, &pid);
  if (pid != cad_pid || !IsWindowVisible(window) || GetWindow(window, 4))
    return 1;
  int rect[4], best[4];
  if (!GetWindowRect(window, rect))
    return 1;
  if (!timer_window || !GetWindowRect(timer_window, best) ||
      (rect[2] - rect[0]) * (rect[3] - rect[1]) >
          (best[2] - best[0]) * (best[3] - best[1]))
    timer_window = window;
  return 1;
}
__declspec(dllimport) U SetFilePointer(P, int, int *, U);
static int InterlockedIncrement(int *p) {
  return __atomic_add_fetch(p, 1, __ATOMIC_SEQ_CST);
}
static int InterlockedDecrement(int *p) {
  return __atomic_sub_fetch(p, 1, __ATOMIC_SEQ_CST);
}
static int same_guid(const GUID *a, const GUID *b) {
  const unsigned char *x = (const unsigned char *)a,
                      *y = (const unsigned char *)b;
  for (U i = 0; i < 16; i++)
    if (x[i] != y[i])
      return 0;
  return 1;
}
static int ui_buttons, ui_typed, ui_themed, ui_null_theme, ui_windows;
__declspec(dllimport) P GetThreadDesktop(U);
__declspec(dllimport) int GetUserObjectInformationW(P, int, P, U, U *);
static void num(const char *label, Q value) {
  say(label);
  milliseconds(value);
}
/* One-shot drop-path diagnostics: first 6 timer ticks, 5 s apart. */
static void diag(void) {
  static Q last;
  static int count;
  Q now = GetTickCount64();
  if (count >= 6 || (count && now - last < 5000))
    return;
  count++;
  last = now;
  P fg = GetForegroundWindow();
  U fg_pid = 0;
  GetWindowThreadProcessId(fg, &fg_pid);
  W desktop[32] = {0};
  GetUserObjectInformationW(GetThreadDesktop(GetCurrentThreadId()), 2, desktop,
                            sizeof(desktop), 0);
  say("diag desktop: ");
  for (U i = 0; desktop[i] && i < 31; i++) {
    char c = (char)desktop[i];
    U w;
    WriteFile(output(), &c, 1, &w, 0);
  }
  say("\r\n");
  num("diag cad_pid: ", cad_pid);
  num("diag GetCurrentProcessId: ", GetCurrentProcessId());
  num("diag foreground hwnd: ", (Q)fg);
  num("diag foreground pid: ", fg_pid);
  num("diag active hwnd: ", (Q)GetActiveWindow());
  num("diag timer_window: ", (Q)timer_window);
  num("diag ui windows/buttons/typed/themed: ", (Q)ui_windows);
  num("  ", (Q)ui_buttons);
  num("  ", (Q)ui_typed);
  num("  ", (Q)ui_themed);
  num("diag ui controls with NULL theme: ", (Q)ui_null_theme);
  focused(cad_pid);
  num("diag focus reason (0 none, 1 fg pid, 2 active window): ",
      (Q)focus_reason);
}
#ifdef SM4L_UI_ADDIN
__declspec(dllimport) int EnumChildWindows(P, int (*)(P, Q), Q);
__declspec(dllimport) int GetClassNameW(P, W *, int);
__declspec(dllimport) long long GetWindowLongPtrW(P, int);
__declspec(dllimport) P GetWindowTheme(P);
__declspec(dllimport) U GetFileAttributesW(const W *);
__declspec(dllimport) long long CallWindowProcW(P, P, U, Q, Q);
__declspec(dllimport) long long SetWindowLongPtrW(P, int, long long);
__declspec(dllimport) int InvalidateRect(P, P, int);
__declspec(dllimport) P GetParent(P);
__declspec(dllimport) int GetWindowTextW(P, W *, int);
__declspec(dllimport) int SetWindowPos(P, P, int, int, int, int, U);
static void hexv(const char *label, Q value) {
  char text[40];
  U n = 0, w;
  while (label[n] && n < 24)
    text[n] = label[n], n++;
  text[n++] = '0';
  text[n++] = 'x';
  for (int i = 15; i >= 0; i--)
    if (value >> (4 * i) || i == 0) {
      text[n++] = "0123456789abcdef"[(value >> (4 * i)) & 15];
    }
  text[n++] = ' ';
  WriteFile(output(), text, n, &w, 0);
}
/* Wine's uxtheme cannot measure themed text: DrawThemeTextEx ignores
 * DTT_CALCRECT and, with themes off, fails with E_HANDLE before touching the
 * rectangle. SolidWorks measures captions (PropertyManager section headers and
 * more) through it, gets back its own zeroed rectangle and lays the header out
 * 0 px wide. Replace both entry points with plain DrawTextW, which keeps the
 * font already selected into the DC. Patching the export covers every module,
 * whether it imports the function or resolves it with GetProcAddress, and every
 * window opened later. Only installed while themes are off: the originals are
 * overwritten and not called. C:\sm4l-dtt-off disables it. */
__declspec(dllimport) P GetModuleHandleW(const W *);
__declspec(dllimport) P GetProcAddress(P, const char *);
__declspec(dllimport) int VirtualProtect(P, Q, U, U *);
__declspec(dllimport) int FlushInstructionCache(P, P, Q);
__declspec(dllimport) P GetCurrentProcess(void);
__declspec(dllimport) int DrawTextW(P, const W *, int, int *, U);
__declspec(dllimport) int SaveDC(P);
__declspec(dllimport) int RestoreDC(P, int);
__declspec(dllimport) int SetBkMode(P, int);
__declspec(dllimport) U SetTextColor(P, U);
__declspec(dllimport) int IsThemeActive(void);
static int dtt_off;
static struct {
  unsigned char *entry;
  unsigned char saved[12];
} patches[2];
static void dtt_log(const char *what, P theme, U flags, const W *text, const int *before,
                    const int *after) {
  static U logged;
  if (logged >= 24)
    return;
  logged++;
  say(what);
  hexv("theme=", (Q)theme);
  hexv("flags=", flags);
  hexv("w0=", (Q)(unsigned)(before[2] - before[0]));
  hexv("w1=", (Q)(unsigned)(after[2] - after[0]));
  char line[48];
  U n = 0, w;
  line[n++] = '[';
  for (int i = 0; text && text[i] && i < 30; i++)
    line[n++] = text[i] >= 32 && text[i] < 127 ? (char)text[i] : '?';
  line[n++] = ']';
  line[n++] = '\r';
  line[n++] = '\n';
  WriteFile(output(), line, n, &w, 0);
}
/* HRESULT DrawThemeTextEx(HTHEME, HDC, part, state, text, cch, flags, RECT *, DTTOPTS *) */
static long dtt_detour(P theme, P hdc, int part, int state, const W *text, int cch, U flags,
                       int *rect, const U *opts) {
  (void)part;
  (void)state;
  if (!hdc || !text || !rect)
    return (long)0x80070057;
  int before[4] = {rect[0], rect[1], rect[2], rect[3]};
  U options = opts ? opts[1] : 0;     /* DTTOPTS.dwFlags */
  int calc = (options & 0x200) != 0;  /* DTT_CALCRECT */
  int saved = SaveDC(hdc);
  if (!calc) {
    SetBkMode(hdc, 1); /* TRANSPARENT, like themed text */
    if (options & 1)   /* DTT_TEXTCOLOR */
      SetTextColor(hdc, opts[2]);
  }
  DrawTextW(hdc, text, cch, rect, flags | (calc ? 0x400 : 0)); /* DT_CALCRECT */
  RestoreDC(hdc, saved);
  dtt_log(calc ? "dtt calc " : "dtt draw ", theme, flags, text, before, rect);
  return 0;
}
/* HRESULT GetThemeTextExtent(HTHEME, HDC, part, state, text, cch, flags, const RECT *bound, RECT *extent) */
static long gte_detour(P theme, P hdc, int part, int state, const W *text, int cch, U flags,
                       const int *bound, int *extent) {
  (void)part;
  (void)state;
  if (!hdc || !text || !extent)
    return (long)0x80070057;
  int box[4] = {0, 0, 32767, 32767}, before[4] = {0, 0, 0, 0};
  if (bound)
    for (int k = 0; k < 4; k++)
      box[k] = bound[k];
  DrawTextW(hdc, text, cch, box, flags | 0x400);
  for (int k = 0; k < 4; k++)
    extent[k] = box[k];
  dtt_log("gte ", theme, flags, text, before, box);
  return 0;
}
static int patch_export(int slot, const char *name, void *detour) {
  P module = GetModuleHandleW(L"uxtheme.dll");
  if (!module)
    return 0;
  unsigned char *entry = (unsigned char *)GetProcAddress(module, name);
  U old;
  if (!entry || !VirtualProtect(entry, 12, 0x40, &old)) /* PAGE_EXECUTE_READWRITE */
    return 0;
  for (int k = 0; k < 12; k++)
    patches[slot].saved[k] = entry[k];
  entry[0] = 0x48; /* mov rax, imm64 ; jmp rax */
  entry[1] = 0xB8;
  *(Q *)(entry + 2) = (Q)detour;
  entry[10] = 0xFF;
  entry[11] = 0xE0;
  VirtualProtect(entry, 12, old, &old);
  FlushInstructionCache(GetCurrentProcess(), entry, 12);
  patches[slot].entry = entry;
  return 1;
}
static void dtt_install(void) {
  if (dtt_off) {
    say("dtt detour: off (opt in with C:\\sm4l-dtt-on)\r\n");
    return;
  }
  if (IsThemeActive()) {
    say("dtt detour: not installed, themes are on\r\n");
    return;
  }
  int a = patch_export(0, "DrawThemeTextEx", (void *)dtt_detour);
  int b = patch_export(1, "GetThemeTextExtent", (void *)gte_detour);
  say("dtt detour installed (DrawThemeTextEx, GetThemeTextExtent): ");
  hexv("", (Q)a);
  hexv("", (Q)b);
  say("\r\n");
}
static void dtt_restore(void) {
  for (int i = 0; i < 2; i++)
    if (patches[i].entry) {
      U old;
      if (VirtualProtect(patches[i].entry, 12, 0x40, &old)) {
        for (int k = 0; k < 12; k++)
          patches[i].entry[k] = patches[i].saved[k];
        VirtualProtect(patches[i].entry, 12, old, &old);
        FlushInstructionCache(GetCurrentProcess(), patches[i].entry, 12);
      }
      patches[i].entry = 0;
    }
}
__declspec(dllimport) P MonitorFromWindow(P, U);
__declspec(dllimport) int IsIconic(P);
__declspec(dllimport) int SetWindowPos(P, P, int, int, int, int, U);
static void center_owned_rect(const int *rect, const int *parent, int *x,
                              int *y) {
  int width = rect[2] - rect[0], height = rect[3] - rect[1];
  int available_x = parent[2] - parent[0] - width;
  int available_y = parent[3] - parent[1] - height;
  *x = parent[0] + (available_x > 0 ? available_x / 2 : 0);
  *y = parent[1] + (available_y > 0 ? available_y / 2 : 0);
}
static int fix_window(P window, Q ignored) {
  (void)ignored;
  U pid = 0;
  GetWindowThreadProcessId(window, &pid);
  if (pid != cad_pid || !IsWindowVisible(window))
    return 1;
  ui_windows++;
  P owner = GetWindow(window, 4);
  int rect[4];
  if (owner && !IsIconic(window) && GetWindowRect(window, rect) &&
      rect[2] > rect[0] && rect[3] > rect[1] && !MonitorFromWindow(window, 0)) {
    int parent[4];
    if (GetWindowRect(owner, parent) && parent[2] > parent[0] &&
        parent[3] > parent[1]) {
      /* Wine can report a monitor work area at x=8600 while the owner is
       * visible. Use the owner's rectangle so recovery cannot repeat there. */
      int x, y;
      center_owned_rect(rect, parent, &x, &y);
      if (SetWindowPos(window, 0, x, y, 0, 0, 0x15))
        say("Recovered an off-screen owned window.\r\n");
    }
  }
  return 1;
}
/* Diagnostic-only mode (C:\sm4l-diag-only exists): no hook, no theme change, no
 * intercept. After the first PropertyManager header shows up, list every
 * Button child (visible or not) of the CAD windows on each tick for 10 s:
 * visibility, theme, sibling z-order, parent, rectangle and caption. */
__declspec(dllimport) int IsAppThemed(void);
__declspec(dllimport) int RedrawWindow(P, const int *, P, U);
__declspec(dllimport) long long SendMessageW(P, U, Q, Q);
static int diag_only;
static Q snap_start;
static int snap_trigger, snap_new, redraw_test;
static P snap_panel;
static U snap_tests;
static Q snap_ms;
static struct {
  P window;
  int rect[4];
  int visible;
} snap_prev[96];
static int (*snap_cb)(P, Q);
static int snap_is_button(P window) {
  W name[8];
  return GetClassNameW(window, name, 8) == 6 && name[0] == 'B' && name[1] == 'u' &&
         name[2] == 't' && name[3] == 't';
}
/* Subclass of the owner-draw Buttons, created by a thread-scoped CBT hook so it
 * is in place before the first layout pass.
 * SolidWorks lays the PropertyManager section headers out with
 * SetWindowPos(hwnd, HWND_TOPMOST, x, y, cx, 13, 0) and every pass under Wine
 * moves the left edge 4 px right with the right edge fixed, until the width
 * reaches 0 (the headers "wipe away"). In WM_WINDOWPOSCHANGING:
 *   A (nozorder): drop the z-order change (SWP_NOZORDER) of those calls;
 *   B (clamp): pin x to the first x the header was given (the smallest seen)
 *     and keep the requested right edge, so the width cannot drift to 0.
 * C:\sm4l-hdr-nozorder-off and C:\sm4l-hdr-clamp-off switch them off. In
 * diag-only mode both stay off and only the passes are logged. */
static struct {
  P window;
  long long original;
  int have, first_x;
  U passes;
} btn_hooks[128];
static int nozorder_on, clamp_on;
__declspec(dllimport) int GetClientRect(P, int *);
__declspec(dllimport) int ClientToScreen(P, int *);
static void geom_log(const char *what, P window) {
  int win[4] = {0, 0, 0, 0}, cli[4] = {0, 0, 0, 0}, org[2] = {0, 0};
  GetWindowRect(window, win);
  GetClientRect(window, cli);
  ClientToScreen(window, org);
  say(what);
  hexv("w=", (Q)window);
  hexv("exstyle=", (Q)(unsigned)GetWindowLongPtrW(window, -20));
  hexv("style=", (Q)(unsigned)GetWindowLongPtrW(window, -16));
  hexv("win_l=", (Q)(unsigned)win[0]);
  hexv("win_t=", (Q)(unsigned)win[1]);
  hexv("win_r=", (Q)(unsigned)win[2]);
  hexv("cli_w=", (Q)(unsigned)cli[2]);
  hexv("cli_h=", (Q)(unsigned)cli[3]);
  hexv("org_x=", (Q)(unsigned)org[0]);
  hexv("org_y=", (Q)(unsigned)org[1]);
  say("\r\n");
}
static long long btn_proc(P window, U message, Q wparam, Q lparam) {
  long long original = 0;
  U slot;
  for (slot = 0; slot < 128; slot++)
    if (btn_hooks[slot].window == window) {
      original = btn_hooks[slot].original;
      break;
    }
  if (!original)
    return 0;
  if (message == 0x46 && lparam) { /* WM_WINDOWPOSCHANGING */
    int *wp = (int *)lparam;       /* hwnd(2), after(2), x, y, cx, cy, flags */
    /* A header row: height 13, moved and resized together. */
    if (wp[7] == 13 && !((U)wp[8] & 3)) {
      U pass = ++btn_hooks[slot].passes;
      int x_in = wp[4], cx_in = wp[6];
      U flags_in = (U)wp[8];
      if (!btn_hooks[slot].have) {
        if (cx_in > 0) {
          btn_hooks[slot].have = 1;
          btn_hooks[slot].first_x = x_in;
        }
      } else if (x_in < btn_hooks[slot].first_x)
        btn_hooks[slot].first_x = x_in;
      if (clamp_on && btn_hooks[slot].have && x_in != btn_hooks[slot].first_x) {
        int right = x_in + cx_in, width = right - btn_hooks[slot].first_x;
        if (width > 0) {
          wp[4] = btn_hooks[slot].first_x;
          wp[6] = width;
        }
      }
      if (nozorder_on)
        wp[8] = (int)((U)wp[8] | 4); /* SWP_NOZORDER */
      if (pass <= 12 || pass % 50 == 0) {
        say("hdr ");
        hexv("w=", (Q)window);
        hexv("pass=", pass);
        hexv("x_in=", (Q)(unsigned)x_in);
        hexv("cx_in=", (Q)(unsigned)cx_in);
        hexv("x_out=", (Q)(unsigned)wp[4]);
        hexv("cx_out=", (Q)(unsigned)wp[6]);
        hexv("flags_in=", flags_in);
        hexv("flags_out=", (Q)(unsigned)wp[8]);
        hexv("x0=", (Q)(unsigned)btn_hooks[slot].first_x);
        say("\r\n");
      }
      static U geoms;
      if (pass == 1 && geoms < 4) {
        geoms++;
        geom_log("geom button ", window);
        geom_log("geom panel ", GetParent(window));
      }
    }
  }
  long long result =
      CallWindowProcW((P)original, window, message, wparam, lparam);
  if (message == 0x82) /* WM_NCDESTROY */
    btn_hooks[slot].window = 0;
  return result;
}
static void btn_hook(P window) {
  U free_slot = 128;
  for (U i = 0; i < 128; i++) {
    if (btn_hooks[i].window == window)
      return;
    if (!btn_hooks[i].window && free_slot == 128)
      free_slot = i;
  }
  if (free_slot == 128)
    return;
  btn_hooks[free_slot].have = 0;
  btn_hooks[free_slot].first_x = 0;
  btn_hooks[free_slot].passes = 0;
  btn_hooks[free_slot].original = 0;
  btn_hooks[free_slot].window = window;
  long long previous = SetWindowLongPtrW(window, -4, (long long)btn_proc);
  if (!previous) {
    btn_hooks[free_slot].window = 0;
    return;
  }
  btn_hooks[free_slot].original = previous;
}
static void btn_unhook(void) {
  for (U i = 0; i < 128; i++)
    if (btn_hooks[i].window) {
      if (GetWindowLongPtrW(btn_hooks[i].window, -4) == (long long)btn_proc)
        SetWindowLongPtrW(btn_hooks[i].window, -4, btn_hooks[i].original);
      btn_hooks[i].window = 0;
    }
}
/* Thread-scoped CBT hook (the UI thread only): subclass owner-draw Buttons
 * when they are created. It touches nothing else and always calls the next
 * hook; the subclass always calls the previous window procedure, so classes
 * SolidWorks subclasses afterwards chain through it. */
__declspec(dllimport) P SetWindowsHookExW(int, long long (*)(int, Q, Q), P, U);
__declspec(dllimport) int UnhookWindowsHookEx(P);
__declspec(dllimport) long long CallNextHookEx(P, int, Q, Q);
static P cbt_hook;
static long long cbt_proc(int code, Q wparam, Q lparam) {
  if (code == 3 && wparam && lparam) { /* HCBT_CREATEWND */
    const char *create = *(const char *const *)lparam; /* CREATESTRUCTW * */
    if (create && ((*(const int *)(create + 48)) & 15) == 11) {
      W name[8];
      if (GetClassNameW((P)wparam, name, 8) == 6 && name[0] == 'B' && name[1] == 'u' &&
          name[2] == 't' && name[3] == 't')
        btn_hook((P)wparam);
    }
  }
  return CallNextHookEx(cbt_hook, code, wparam, lparam);
}
static void cbt_install(void) {
  if (!cbt_hook)
    cbt_hook = SetWindowsHookExW(5, cbt_proc, 0, GetCurrentThreadId());
  say(cbt_hook ? "CBT hook installed (UI thread)\r\n" : "CBT hook failed\r\n");
}
static void cbt_remove(void) {
  if (cbt_hook) {
    UnhookWindowsHookEx(cbt_hook);
    cbt_hook = 0;
  }
}
static int snap_detect(P window, Q ignored) {
  (void)ignored;
  W caption[2];
  if (IsWindowVisible(window) && snap_is_button(window) &&
      ((U)GetWindowLongPtrW(window, -16) & 15) == 11 &&
      GetWindowTextW(window, caption, 2)) {
    snap_trigger = 1;
    if (!snap_panel)
      snap_panel = GetParent(window);
    btn_hook(window);
    /* A header button we have not seen yet means a new panel opened: restart
     * the 15 s window so every opening is captured. */
    U i;
    for (i = 0; i < 96 && snap_prev[i].window != window; i++)
      ;
    if (i == 96) {
      for (i = 0; i < 96 && snap_prev[i].window; i++)
        ;
      if (i < 96) {
        snap_prev[i].window = window;
        snap_prev[i].visible = -1;
      }
      snap_new = 1;
    }
  }
  return 1;
}
static int snap_list(P window, Q ignored) {
  (void)ignored;
  if (!snap_is_button(window))
    return 1;
  W text[22];
  int len = GetWindowTextW(window, text, 22);
  U style = (U)GetWindowLongPtrW(window, -16) & 15;
  /* Captioned owner-draw Buttons only (the section headers). */
  if (!len || style != 11)
    return 1;
  P parent = GetParent(window);
  U z = 0;
  for (P w = GetWindow(parent, 5); w && w != window && z < 500; w = GetWindow(w, 2))
    z++;
  int rect[4] = {0, 0, 0, 0};
  GetWindowRect(window, rect);
  int visible = IsWindowVisible(window);
  /* Log a control the first time it is seen and whenever its rectangle or
   * visibility changes, so a fast timer does not flood the log. */
  U slot = 96;
  for (U i = 0; i < 96; i++)
    if (snap_prev[i].window == window) {
      slot = i;
      break;
    }
  if (slot == 96)
    for (U i = 0; i < 96; i++)
      if (!snap_prev[i].window) {
        slot = i;
        snap_prev[i].window = window;
        snap_prev[i].visible = -1;
        break;
      }
  if (slot < 96) {
    if (snap_prev[slot].visible == visible && snap_prev[slot].rect[0] == rect[0] &&
        snap_prev[slot].rect[1] == rect[1] && snap_prev[slot].rect[2] == rect[2] &&
        snap_prev[slot].rect[3] == rect[3])
      return 1;
    snap_prev[slot].visible = visible;
    for (int k = 0; k < 4; k++)
      snap_prev[slot].rect[k] = rect[k];
  }
  char line[160];
  U n = 0, w2;
  line[n++] = 's';
  line[n++] = ' ';
  line[n++] = IsWindowVisible(window) ? 'V' : 'h';
  line[n++] = GetWindowTheme(window) ? 'T' : '-';
  line[n++] = "0123456789abcdef"[style];
  line[n++] = ' ';
  for (int i = 0; i < len && i < 21 && n < 80; i++)
    line[n++] = text[i] >= 32 && text[i] < 127 ? (char)text[i] : '?';
  line[n++] = ' ';
  WriteFile(output(), line, n, &w2, 0);
  hexv("w=", (Q)window);
  hexv("p=", (Q)parent);
  hexv("z=", z);
  for (int k = 0; k < 4; k++)
    hexv("r=", (Q)(unsigned)rect[k]);
  int client[4] = {0, 0, 0, 0};
  GetClientRect(parent, client);
  hexv("pw=", (Q)(unsigned)client[2]);
  hexv("ph=", (Q)(unsigned)client[3]);
  hexv("ms=", snap_ms);
  say("\r\n");
  return 1;
}
static int snap_top(P window, Q ignored) {
  (void)ignored;
  U pid = 0;
  GetWindowThreadProcessId(window, &pid);
  if (pid == cad_pid && IsWindowVisible(window))
    EnumChildWindows(window, snap_cb, 0);
  return 1;
}
__declspec(dllimport) P GetDC(P);
__declspec(dllimport) int ReleaseDC(P, P);
__declspec(dllimport) P SelectObject(P, P);
__declspec(dllimport) int GetTextExtentPoint32W(P, const W *, int, int *);
/* One-shot: measure a header caption the way SolidWorks does (DrawTextW with
 * DT_CALCRECT, flags seen in the relay trace) on the panel's own DC and font,
 * with a zero-width and a wide input rectangle, and log what Wine returns. */
static void dt_probe(P panel) {
  static const W text[] = {'F', 'i', 'l', 'l', 'e', 't', ' ', 'T', 'y', 'p', 'e', 0};
  P dc = GetDC(panel);
  if (!dc)
    return;
  Q font = (Q)SendMessageW(panel, 0x31, 0, 0); /* WM_GETFONT */
  P old = font ? SelectObject(dc, (P)font) : 0;
  hexv("dtprobe panel=", (Q)panel);
  hexv("font=", font);
  say("\r\n");
  static const U flags[2] = {0x410, 0x420};
  static const int widths[5] = {200, 50, 10, 0, -4};
  for (int j = 0; j < 5; j++)
    for (int i = 0; i < 2; i++) {
      int rect[4] = {0, 0, widths[j], 13};
      int ret = DrawTextW(dc, text, 11, rect, flags[i]);
      hexv("dtprobe flags=", flags[i]);
      hexv("in_right=", (Q)(unsigned)widths[j]);
      hexv("ret_h=", (Q)(unsigned)ret);
      hexv("out_left=", (Q)(unsigned)rect[0]);
      hexv("out_right=", (Q)(unsigned)rect[2]);
      hexv("out_bottom=", (Q)(unsigned)rect[3]);
      say("\r\n");
    }
  int size[2] = {0, 0};
  int ok = GetTextExtentPoint32W(dc, text, 11, size);
  hexv("dtprobe GetTextExtentPoint32W ok=", (Q)ok);
  hexv("cx=", (Q)(unsigned)size[0]);
  hexv("cy=", (Q)(unsigned)size[1]);
  say("\r\n");
  if (old)
    SelectObject(dc, old);
  ReleaseDC(panel, dc);
}
static void snapshot(void) {
  snap_trigger = snap_new = 0;
  snap_cb = snap_detect;
  EnumWindows(snap_top, 0);
  Q now = GetTickCount64();
  if (snap_new || (snap_trigger && !snap_start)) {
    snap_start = now;
    snap_tests = 0;
    snap_panel = 0;
    say("snapshot start; IsThemeActive/IsAppThemed: ");
    hexv("", (Q)IsThemeActive());
    hexv("", (Q)IsAppThemed());
    say("\r\n");
  }
  if (snap_start && now - snap_start < 15000) {
    snap_ms = now - snap_start;
    snap_cb = snap_list;
    EnumWindows(snap_top, 0);
    /* Optional repaint/layout probes (C:\sm4l-redraw-test exists): a repaint with
     * no geometry change at +3 s, then a WM_SIZE with the unchanged size at +8 s.
     * Watch whether the header captions survive each one. */
    if (snap_panel && snap_ms >= 1000 && !(snap_tests & 4)) {
      snap_tests |= 4;
      dt_probe(snap_panel);
    }
    if (redraw_test && snap_panel) {
      if (snap_ms >= 3000 && !(snap_tests & 1)) {
        snap_tests |= 1;
        RedrawWindow(snap_panel, 0, 0, 0x1 | 0x4 | 0x80 | 0x100);
        hexv("PROBE redraw (no geometry change) ms=", snap_ms);
        say("\r\n");
      }
      if (snap_ms >= 8000 && !(snap_tests & 2)) {
        snap_tests |= 2;
        int client[4] = {0, 0, 0, 0};
        GetClientRect(snap_panel, client);
        SendMessageW(snap_panel, 5, 0, (Q)(((U)client[3] << 16) | ((U)client[2] & 0xffff)));
        hexv("PROBE WM_SIZE same size ms=", snap_ms);
        say("\r\n");
      }
    }
  }
}
static void tick(P window, U message, Q id, U time) {
  (void)message;
  (void)id;
  (void)time;
  if (busy || !cad)
    return;
  busy = 1;
  (void)window;
  static int cbt_tried;
  if (!cbt_tried && (clamp_on || nozorder_on || diag_only)) {
    cbt_tried = 1;
    cbt_install();
  }
  if (diag_only) {
    snapshot();
    diag();
    busy = 0;
    return;
  }
  ui_windows = ui_buttons = ui_typed = ui_themed = ui_null_theme = 0;
  EnumWindows(fix_window, 0);
  diag();
  busy = 0;
}
#else
static void tick(P window, U message, Q id, U time) {
  (void)window;
  (void)message;
  (void)id;
  (void)time;
  if (busy || !cad)
    return;
  static int first_tick;
  if (!first_tick++) {
    say("UI timer is dispatching.\r\n");
  }
  diag();
  Packet p;
  if (!read_packet(&p) || p.seq == last_sequence)
    return;
  last_sequence = p.seq;
  if (!focused(cad_pid))
    return;
  busy = 1;
  Q start = GetTickCount64();
  VAR doc = {0}, view = {0};
  H h = view_of(cad, &doc, &view);
  if (h >= 0 && focused(cad_pid))
    h = apply(view.val.ptr, doc.val.ptr, &p);
  VariantClear(&view);
  VariantClear(&doc);
  static Q total;
  static U frames;
  static H previous;
  if (h >= 0) {
    previous = 0;
    total += GetTickCount64() - start;
    if (++frames == 30) {
      say("Average in-process view frame (ms): ");
      milliseconds(total / frames);
      total = 0;
      frames = 0;
    }
  } else if (h != (H)0x80040005 && h != previous) {
    report(h);
    previous = h;
  }
  busy = 0;
}
#endif
static int object_refs = 1, factory_refs = 1, locks;
static U object_add(P self) {
  (void)self;
  return (U)InterlockedIncrement(&object_refs);
}
static U object_release(P self) {
  (void)self;
  return (U)InterlockedDecrement(&object_refs);
}
static H object_query(P self, const GUID *i, P *out) {
  if (!out)
    return (H)0x80004003;
  *out = 0;
  if (!same_guid(i, &unknown_iid) && !same_guid(i, &addin_iid))
    return (H)0x80004002;
  *out = self;
  object_add(self);
  return 0;
}
static H disconnect(P self, short *out) {
  (void)self;
#ifdef SM4L_UI_ADDIN
  cbt_remove();
  btn_unhook();
  dtt_restore();
#endif
  if (timer) {
    KillTimer(timer_window, timer); /* NULL window while still waiting */
    timer = 0;
  }
  if (cad) {
    cad->v->release(cad);
    cad = 0;
  }
  if (output_handle) {
    CloseHandle(output_handle);
    output_handle = 0;
  }
  if (out)
    *out = -1;
  return 0;
}
static Q connect_time;
static Q start_timer(void) {
#ifdef SM4L_UI_ADDIN
  return SetTimer(timer_window, 0x534d3455, diag_only ? 30 : 500, tick);
#else
  return SetTimer(timer_window, 0x534d344c, 16, tick);
#endif
}
static void wait_tick(P window, U message, Q id, U time) {
  (void)window;
  (void)message;
  (void)id;
  (void)time;
  if (!cad || GetTickCount64() - connect_time < 5000)
    return;
  /* Ready = a large, enabled CAD frame (no splash) that has stayed that way
   * for 6 s. Anything less and we keep our hands off the UI. */
  static Q ready_since;
  timer_window = 0;
  EnumWindows(pick_window, 0);
  int rect[4];
  if (!timer_window || !IsWindowEnabled(timer_window) ||
      !GetWindowRect(timer_window, rect) || rect[2] - rect[0] < 640 ||
      rect[3] - rect[1] < 480) {
    ready_since = 0;
    timer_window = 0;
    return;
  }
  if (!ready_since)
    ready_since = GetTickCount64();
  if (GetTickCount64() - ready_since < 6000)
    return;
  KillTimer(0, timer);
#ifdef SM4L_UI_ADDIN
  if (!diag_only)
    dtt_install();
#endif
  timer = start_timer();
  if (!timer) {
    say("Cannot start the input timer.\r\n");
    return;
  }
  say("CAD UI thread: ");
  milliseconds(GetWindowThreadProcessId(timer_window, 0));
}
static H connect(P self, OBJ *application, int cookie, short *out) {
  (void)cookie;
  if (!out)
    return (H)0x80004003;
  *out = 0;
  disconnect(self, 0);
  H h = application->v->query(application, &iid, (P *)&cad);
  if (h < 0)
    return h;
  VAR pid = {0};
  h = call(cad, L"GetProcessID", 1, &pid);
  if (h < 0 || pid.vt != 3) {
    disconnect(self, 0);
    return (H)0x80004005;
  }
  cad_pid = (U)pid.val.num;
#ifdef SM4L_UI_ADDIN
  const W *log_path = L"C:\\sm4l-ui-compat.log";
#else
  const W *log_path = L"C:\\sm4l-spacemouse-addin.log";
#endif
  P log = CreateFileW(log_path, 0x40000000, 7, 0, 4, 0x80, 0);
  if (log != (P)-1) {
    output_handle = log;
    SetFilePointer(log, 0, 0, 2);
  }
#ifndef SM4L_UI_ADDIN
  last_sequence = 0;
#endif
  /* CAD may load us during startup, before its frame exists. Touch no
   * window yet: a plain thread timer polls until a frame has been visible
   * for a few seconds, then wait_tick arms the real UI timer. */
  timer_window = 0;
  connect_time = GetTickCount64();
  say("Connect thread: ");
  milliseconds(GetCurrentThreadId());
  timer = SetTimer(0, 0, 500, wait_tick);
  if (!timer) {
    disconnect(self, 0);
    return (H)0x80004005;
  }
#ifdef SM4L_UI_ADDIN
  /* Both on by default. C:\sm4l-erase-off turns the erase/print intercept
   * off and C:\sm4l-clip-off turns the WS_CLIPCHILDREN fix off, so one run can
   * tell which of them helps. */
  diag_only = GetFileAttributesW(L"C:\\sm4l-diag-only") != 0xffffffffu;
  say(diag_only ? "DIAG ONLY: no hook, no theme change, no intercept\r\n" : "");
  nozorder_on = !diag_only && GetFileAttributesW(L"C:\\sm4l-hdr-nozorder-off") == 0xffffffffu;
  clamp_on = !diag_only && GetFileAttributesW(L"C:\\sm4l-hdr-clamp-off") == 0xffffffffu;
  say(nozorder_on ? "header fix A (no z-order): ON\r\n" : "header fix A (no z-order): off\r\n");
  say(clamp_on ? "header fix B (pin x): ON\r\n" : "header fix B (pin x): off\r\n");
  redraw_test = GetFileAttributesW(L"C:\\sm4l-redraw-test") != 0xffffffffu;
  dtt_off = GetFileAttributesW(L"C:\\sm4l-dtt-on") == 0xffffffffu; /* on hold: opt in with this file */
  say("SM4L UI compatibility connected.\r\n");
#else
  say("SM4L in-process SpaceMouse connected.\r\n");
#endif
  *out = -1;
  return 0;
}
static AV object_vtable = {object_query, object_add, object_release, connect,
                           disconnect};
static struct {
  AV *v;
} object = {&object_vtable};
static U factory_add(P self) {
  (void)self;
  return (U)InterlockedIncrement(&factory_refs);
}
static U factory_release(P self) {
  (void)self;
  return (U)InterlockedDecrement(&factory_refs);
}
static H factory_query(P self, const GUID *i, P *out) {
  if (!out)
    return (H)0x80004003;
  *out = 0;
  if (!same_guid(i, &unknown_iid) && !same_guid(i, &factory_iid))
    return (H)0x80004002;
  *out = self;
  factory_add(self);
  return 0;
}
static H create(P self, P outer, const GUID *i, P *out) {
  (void)self;
  if (outer)
    return (H)0x80040110;
  return object_query(&object, i, out);
}
static H lock(P self, int state) {
  (void)self;
  if (state)
    InterlockedIncrement(&locks);
  else
    InterlockedDecrement(&locks);
  return 0;
}
static FV factory_vtable = {factory_query, factory_add, factory_release, create,
                            lock};
static struct {
  FV *v;
} factory = {&factory_vtable};
__declspec(dllexport) H DllGetClassObject(const GUID *c, const GUID *i,
                                          P *out) {
  if (!same_guid(c, &clsid))
    return (H)0x80040111;
  return factory_query(&factory, i, out);
}
__declspec(dllexport) H DllCanUnloadNow(void) {
  return !cad && !busy && object_refs <= 1 && factory_refs <= 1 && !locks ? 0
                                                                          : 1;
}
#endif
