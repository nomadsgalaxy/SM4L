// Reproduce the null HDM_LAYOUT from the SOLIDWORKS minidump; validate real layouts first.
typedef unsigned short WCHAR; typedef unsigned long long U; typedef long long S; typedef void *P;
typedef struct {unsigned size,classes;} INIT;
typedef struct {int left,top,right,bottom;} RECT;
typedef struct {P hwnd,after;int x,y,cx,cy;unsigned flags;} POS;
typedef struct {RECT *rect; POS *pos;} LAYOUT;
__declspec(dllimport) void ExitProcess(unsigned);
__declspec(dllimport) P AddVectoredExceptionHandler(unsigned,P);
__declspec(dllimport) int InitCommonControlsEx(INIT *);
__declspec(dllimport) P CreateWindowExW(unsigned,const WCHAR *,const WCHAR *,unsigned,int,int,int,int,P,P,P,P);
__declspec(dllimport) S SendMessageW(P,unsigned,U,S);
__declspec(dllimport) int DestroyWindow(P);
static S crash(P unused){(void)unused;ExitProcess(2);return 0;}
void entry(void){
 AddVectoredExceptionHandler(1,(P)crash);INIT init={8,0x4000};if(!InitCommonControlsEx(&init))ExitProcess(3);
 P parent=CreateWindowExW(0,L"STATIC",L"Header probe",0,0,0,200,100,0,0,0,0);
 P header=CreateWindowExW(0,L"SysHeader32",L"",0x40000000,0,0,200,30,parent,0,0,0);
 if(!parent||!header)ExitProcess(4);
 RECT rect={0,0,200,100};POS pos={0};LAYOUT layout={&rect,&pos};
 if(!SendMessageW(header,0x1205,0,(S)&layout)||pos.cx!=200||pos.cy<=0||rect.top!=pos.cy)ExitProcess(5);
 if(SendMessageW(header,0x1205,0,0))ExitProcess(6);
 DestroyWindow(header);DestroyWindow(parent);ExitProcess(0);
}
