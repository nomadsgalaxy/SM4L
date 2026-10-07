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
static int focused(U pid) {
  U current = 0;
  GetWindowThreadProcessId(GetForegroundWindow(), &current);
  return current == pid;
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
    if (h >= 0 || option(L"--check-view") || h != (H)0x800401e3 ||
        attempt == 179)
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
  P process = OpenProcess(0x101000, 0, (U)pid.val.num);
  if (!process) {
    say("Cannot watch the CAD process.\r\n");
    ExitProcess(4);
  }
  if (option(L"--load-addin") || option(L"--unload-addin")) {
    VAR file = {0}, result = {0};
    file.vt = 8;
    file.val.ptr = SysAllocString(L"C:\\sm4l-spacemouse-v3.dll");
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
    say("In-process SpaceMouse add-in loaded.\r\n");
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
static const GUID clsid = {0xbb75177c,
                           0x6799,
                           0x4f57,
                           {0x9b, 0x75, 0x10, 0x93, 0x1d, 0x64, 0x21, 0xf6}};
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
static U cad_pid, last_sequence;
static int busy;
__declspec(dllimport) Q SetTimer(P, Q, U, void (*)(P, U, Q, U));
__declspec(dllimport) int KillTimer(P, Q);
__declspec(dllimport) int EnumWindows(int (*)(P, Q), Q);
__declspec(dllimport) int IsWindowVisible(P);
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
  if (timer) {
    KillTimer(timer_window, timer);
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
  P log = CreateFileW(L"C:\\sm4l-spacemouse-addin.log", 0x40000000, 7, 0, 4,
                      0x80, 0);
  if (log != (P)-1) {
    output_handle = log;
    SetFilePointer(log, 0, 0, 2);
  }
  last_sequence = 0;
  timer_window = 0;
  EnumWindows(pick_window, 0);
  if (!timer_window) {
    say("No visible CAD frame for the input timer.\r\n");
    disconnect(self, 0);
    return (H)0x80004005;
  }
  say("Connect thread: ");
  milliseconds(GetCurrentThreadId());
  say("CAD UI thread: ");
  milliseconds(GetWindowThreadProcessId(timer_window, 0));
  timer = SetTimer(timer_window, 0x534d344c, 16, tick);
  if (!timer) {
    disconnect(self, 0);
    return (H)0x80004005;
  }
  say("SM4L in-process SpaceMouse connected.\r\n");
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
