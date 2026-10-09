// CAD install helper (INSTALL step 8, built by the commands in tests/test_cad_msi_build.py). Run setup/prepare_design_install.py first: it
// extracts and CRC-checks spatialiop.zip into INSTALLDIR/spiop/files.
// ponytail: pinned local 2026 SP3.0/default Steam profile; generalize only after CAD startup works.
typedef unsigned short WCHAR;
typedef unsigned HANDLE;
__declspec(dllimport) unsigned MsiSetInternalUI(unsigned,void *);
__declspec(dllimport) unsigned MsiEnableLogW(unsigned,const WCHAR *,unsigned);
__declspec(dllimport) unsigned MsiInstallProductW(const WCHAR *,const WCHAR *);
__declspec(dllimport) unsigned MsiOpenDatabaseW(const WCHAR *,const WCHAR *,HANDLE *);
__declspec(dllimport) unsigned MsiDatabaseOpenViewW(HANDLE,const WCHAR *,HANDLE *);
__declspec(dllimport) unsigned MsiViewExecute(HANDLE,HANDLE);
__declspec(dllimport) unsigned MsiViewFetch(HANDLE,HANDLE *);
__declspec(dllimport) unsigned MsiRecordGetStringW(HANDLE,unsigned,WCHAR *,unsigned *);
__declspec(dllimport) unsigned MsiDatabaseCommit(HANDLE);
__declspec(dllimport) unsigned MsiCloseHandle(HANDLE);
__declspec(dllimport) void ExitProcess(unsigned);
#define PACKAGE L"C:\\users\\steamuser\\Downloads\\3DEXPERIENCE SOLIDWORKS Downloads\\2026 SP3.0\\swwi\\data\\solidworks-proton-preextracted.msi"
static void check(unsigned r) { if(r) ExitProcess(r); }
void entry(void) {
 HANDLE db=0,view=0,record=0; WCHAR target[128]; unsigned n=128;
 check(MsiOpenDatabaseW(PACKAGE,(const WCHAR *)1,&db));
 check(MsiDatabaseOpenViewW(db,L"SELECT `Target` FROM `CustomAction` WHERE `Action` = 'InstallSpatialIOP'",&view));
 check(MsiViewExecute(view,0)); check(MsiViewFetch(view,&record));
 check(MsiRecordGetStringW(record,1,target,&n));
 const WCHAR *expected=L"WIDll_InstallSpatialIOP";
 for(unsigned i=0;;i++){if(target[i]!=expected[i])ExitProcess(87);if(!expected[i])break;}
 MsiCloseHandle(record);MsiCloseHandle(view);
 check(MsiDatabaseOpenViewW(db,L"UPDATE `InstallExecuteSequence` SET `Condition` = '0' WHERE `Action` = 'InstallSpatialIOP'",&view));
 check(MsiViewExecute(view,0)); MsiCloseHandle(view);
 check(MsiDatabaseCommit(db));MsiCloseHandle(db);
 MsiSetInternalUI(2,0);
 check(MsiEnableLogW(0x3fff,L"C:\\sw-design-preextracted.log",0));
 check(MsiInstallProductW(PACKAGE,L"SWXIM=1 SLDIM=1 ARPSYSTEMCOMPONENT=1 REBOOT=ReallySuppress INSTALLDIR=\"C:\\Program Files\\Dassault Systemes\\SOLIDWORKS Apps 2026\\SOLIDWORKS\" ADDLOCAL=ALL TOOLBOXFOLDER=\"C:\\users\\Public\\Documents\\SOLIDWORKS\\SOLIDWORKS Data\" OFFICEOPTION=3"));
 ExitProcess(0);
}
