// Exercise Chromium's child-memory allocation/write sequence without WebView2.
typedef void *HANDLE; typedef unsigned DWORD; typedef unsigned short WORD;
typedef unsigned long long SIZE_T;
typedef struct {DWORD cb; void *reserved,*desktop,*title; DWORD x,y,xsize,ysize,xchars,ychars,fill,flags; WORD show,reserved_bytes; void *reserved_data; HANDLE input,output,error;} STARTUP;
typedef struct {HANDLE process,thread; DWORD pid,tid;} PROCESS;
__declspec(dllimport) int CreateProcessW(const unsigned short*,unsigned short*,void*,void*,int,DWORD,void*,const unsigned short*,STARTUP*,PROCESS*);
__declspec(dllimport) DWORD GetModuleFileNameW(HANDLE,unsigned short*,DWORD);
__declspec(dllimport) void *VirtualAllocEx(HANDLE,void*,SIZE_T,DWORD,DWORD);
__declspec(dllimport) int WriteProcessMemory(HANDLE,void*,const void*,SIZE_T,SIZE_T*);
__declspec(dllimport) int ReadProcessMemory(HANDLE,const void*,void*,SIZE_T,SIZE_T*);
__declspec(dllimport) int VirtualFreeEx(HANDLE,void*,SIZE_T,DWORD);
__declspec(dllimport) int TerminateProcess(HANDLE,unsigned);
__declspec(dllimport) int CloseHandle(HANDLE);
__declspec(dllimport) DWORD GetLastError(void);
__declspec(dllimport) void ExitProcess(DWORD);
__declspec(dllimport) HANDLE CreateFileW(const unsigned short*,DWORD,DWORD,void*,DWORD,DWORD,HANDLE);
__declspec(dllimport) int WriteFile(HANDLE,const void*,DWORD,DWORD*,void*);
static void report(const char *stage,DWORD code) {
 char b[120];DWORD n=0,w; while(*stage)b[n++]=*stage++;
 b[n++]=' '; char digits[10];unsigned k=0;do {digits[k++]=(char)('0'+code%10);code/=10;}while(code);while(k)b[n++]=digits[--k];b[n++]='\n';
 HANDLE f=CreateFileW(L"C:\\child_memory_probe.txt",0x40000000,3,0,2,0x80,0);WriteFile(f,b,n,&w,0);CloseHandle(f);
}
void entry(void) {
 unsigned short exe[1024];GetModuleFileNameW(0,exe,1024);
 STARTUP s={0};PROCESS p={0};s.cb=sizeof(s);
 if(!CreateProcessW(exe,0,0,0,0,4,0,0,&s,&p)){DWORD e=GetLastError();report("CreateProcess failed",e);ExitProcess(1);}
 void *remote=VirtualAllocEx(p.process,0,4096,0x1000,4);DWORD error=0;const char *stage="PASS: real child memory roundtrip";
 unsigned value=0x1234abcd,read=0;SIZE_T n=0;
 if(!remote){error=GetLastError();stage="VirtualAllocEx failed";}
 else if(!WriteProcessMemory(p.process,remote,&value,sizeof(value),&n)||n!=sizeof(value)){error=GetLastError();stage="WriteProcessMemory failed";}
 else if(!ReadProcessMemory(p.process,remote,&read,sizeof(read),&n)||n!=sizeof(read)||read!=value){error=GetLastError();stage="ReadProcessMemory verification failed";}
 if(remote)VirtualFreeEx(p.process,remote,0,0x8000);
 TerminateProcess(p.process,0);CloseHandle(p.thread);CloseHandle(p.process);report(stage,error);ExitProcess(error?error:(stage[0]=='P'?0:1));
}
