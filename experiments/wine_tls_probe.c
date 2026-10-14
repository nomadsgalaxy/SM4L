#include "windef.h"
#include "winbase.h"
#include "winternl.h"

static HANDLE ready, go;
static DWORD *slot;
static unsigned failures;
static void check(int ok, const char *message)
{
    DWORD written, length = 0;
    if (ok) return;
    failures++;
    while (message[length]) length++;
    WriteFile(GetStdHandle(STD_OUTPUT_HANDLE), message, length, &written, 0);
}
static DWORD WINAPI worker(void *phase)
{
    DWORD *data;
    if (!phase) { SetEvent(ready); WaitForSingleObject(go, 10000); }
    data = ((void **)NtCurrentTeb()->ThreadLocalStoragePointer)[*slot];
    if (phase == (void *)2) check(!data, "FAIL: TLS survived release in a new thread\n");
    else {
        check(data && data[0] == 42 && data[1] == 0, "FAIL: thread template or zero fill\n");
        if (data) data[0] = 123;
    }
    return 0;
}
void mainCRTStartup(void)
{
    NTSTATUS (WINAPI *handle)(LDR_DATA_TABLE_ENTRY *);
    void (WINAPI *release)(LDR_DATA_TABLE_ENTRY *, ULONG);
    HMODULE ntdll = GetModuleHandleA("ntdll.dll");
    BYTE *image = VirtualAlloc(0, 0x2000, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    IMAGE_DOS_HEADER *dos = (void *)image;
    IMAGE_NT_HEADERS *nt = (void *)(image + 0x100);
    IMAGE_TLS_DIRECTORY *tls = (void *)(image + 0x800);
    LDR_DATA_TABLE_ENTRY mod;
    HANDLE old, fresh;
    DWORD *data, result, written;
    unsigned i;
    for (i = 0; i < sizeof(mod); i++) ((volatile BYTE *)&mod)[i] = 0;
    handle = (void *)GetProcAddress(ntdll, "LdrpHandleTlsData");
    release = (void *)GetProcAddress(ntdll, "LdrpReleaseTlsEntry");
    check(handle && release, "FAIL: TLS compatibility entry points absent\n");
    if (!handle || !release || !image) ExitProcess(1);
    dos->e_magic = IMAGE_DOS_SIGNATURE; dos->e_lfanew = 0x100;
    nt->Signature = IMAGE_NT_SIGNATURE;
    nt->OptionalHeader.Magic = IMAGE_NT_OPTIONAL_HDR64_MAGIC;
    nt->OptionalHeader.SizeOfImage = 0x2000;
    nt->OptionalHeader.NumberOfRvaAndSizes = 16;
    nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_TLS].VirtualAddress = 0x800;
    nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_TLS].Size = sizeof(*tls);
    tls->StartAddressOfRawData = (ULONG_PTR)(image + 0x900);
    tls->EndAddressOfRawData = tls->StartAddressOfRawData + 4;
    tls->AddressOfIndex = (ULONG_PTR)(image + 0x920);
    tls->SizeOfZeroFill = 4;
    *(DWORD *)(image + 0x900) = 42;
    slot = (void *)(image + 0x920); mod.DllBase = image;
    check(handle(0) < 0, "FAIL: null entry accepted\n");
    ready = CreateEventA(0, TRUE, FALSE, 0); go = CreateEventA(0, TRUE, FALSE, 0);
    old = CreateThread(0, 0, worker, 0, 0, 0);
    check(WaitForSingleObject(ready, 10000) == WAIT_OBJECT_0, "FAIL: existing thread did not start\n");
    check(handle(&mod) == 0, "FAIL: real TLS registration failed\n");
    data = ((void **)NtCurrentTeb()->ThreadLocalStoragePointer)[*slot];
    check(data && data[0] == 42 && data[1] == 0, "FAIL: main template or zero fill\n");
    if (data) data[0] = 99;
    SetEvent(go); WaitForSingleObject(old, 10000);
    GetExitCodeThread(old, &result); check(result == 0, "FAIL: existing thread failed\n");
    fresh = CreateThread(0, 0, worker, (void *)1, 0, 0); WaitForSingleObject(fresh, 10000);
    GetExitCodeThread(fresh, &result); check(result == 0, "FAIL: new thread failed\n");
    check(data && data[0] == 99, "FAIL: TLS data shared between threads\n");
    release(&mod, 0);
    CloseHandle(fresh);
    fresh = CreateThread(0, 0, worker, (void *)2, 0, 0); WaitForSingleObject(fresh, 10000);
    GetExitCodeThread(fresh, &result); check(result == 0, "FAIL: post-release thread failed\n");
    if (!failures) WriteFile(GetStdHandle(STD_OUTPUT_HANDLE), "PASS: static TLS template, zero fill, existing/new threads, isolation and release\n", sizeof("PASS: static TLS template, zero fill, existing/new threads, isolation and release\n") - 1, &written, 0);
    ExitProcess(failures ? 1 : 0);
}
