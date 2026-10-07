// Reproduce WebView2's startup signal with only EVENT_MODIFY_STATE access.
typedef void *HANDLE;
typedef unsigned DWORD;
__declspec(dllimport) HANDLE CreateEventW(void *,int,int,const unsigned short *);
__declspec(dllimport) HANDLE GetCurrentProcess(void);
__declspec(dllimport) int DuplicateHandle(HANDLE,HANDLE,HANDLE,HANDLE *,DWORD,int,DWORD);
__declspec(dllimport) int SetEvent(HANDLE);
__declspec(dllimport) DWORD WaitForSingleObject(HANDLE,DWORD);
__declspec(dllimport) DWORD GetLastError(void);
__declspec(dllimport) void ExitProcess(DWORD);
__declspec(dllimport) HANDLE CreateFileW(const unsigned short *,DWORD,DWORD,void *,DWORD,DWORD,HANDLE);
__declspec(dllimport) int WriteFile(HANDLE,const void *,DWORD,DWORD *,void *);
static void report(const char *s) {
 DWORD n=0,w; while(s[n])n++; HANDLE f=CreateFileW(L"C:\\event_signal_probe.txt",0x40000000,3,0,2,0x80,0); WriteFile(f,s,n,&w,0);
}
void entry(void) {
 HANDLE e=CreateEventW(0,1,0,0),d=0,p=GetCurrentProcess();
 if(!e || !DuplicateHandle(p,e,p,&d,2,0,0)) { report("setup failed\n"); ExitProcess(2); }
 if(!SetEvent(d)) { DWORD err=GetLastError(); report("SetEvent(EVENT_MODIFY_STATE) failed\n"); ExitProcess(err); }
 if(WaitForSingleObject(e,0)!=0) { report("event was not signaled\n"); ExitProcess(3); }
 report("PASS: limited-access handle signals the real event\n"); ExitProcess(0);
}
