/* RtlIsNameInExpression compatibility implementation.
 * Contract: https://learn.microsoft.com/windows/win32/devnotes/rtlisnameinexpression
 * DOS wildcard rules: dotnet/runtime FileSystemName.cs and ReactOS API tests.
 * No matching result is fabricated; all other lookups use the real provider.
 */
typedef unsigned short WCHAR;
typedef unsigned char BOOLEAN;
typedef struct { unsigned short Length, MaximumLength; WCHAR *Buffer; } UNICODE_STRING;
#ifdef _WIN32
__declspec(dllimport) void *GetProcessHeap(void);
__declspec(dllimport) void *HeapAlloc(void *, unsigned long, unsigned long long);
__declspec(dllimport) int HeapFree(void *, unsigned long, void *);
__declspec(dllimport) WCHAR RtlUpcaseUnicodeChar(WCHAR);
__declspec(dllimport) void RtlRaiseStatus(long);
#define allocate(n) HeapAlloc(GetProcessHeap(),8,(n))
#define release(p) HeapFree(GetProcessHeap(),0,(p))
#define uppercase(c) RtlUpcaseUnicodeChar(c)
#else
#include <stdlib.h>
#include <wctype.h>
#define allocate(n) calloc(1,(n))
#define release(p) free(p)
#define uppercase(c) ((WCHAR)towupper(c))
#endif

BOOLEAN sw_match(const UNICODE_STRING *expr, const UNICODE_STRING *name,
                 BOOLEAN ignore_case, const WCHAR *table) {
    if (!expr || !name || (expr->Length & 1) || (name->Length & 1) ||
        expr->Length > expr->MaximumLength || name->Length > name->MaximumLength ||
        (expr->Length && !expr->Buffer) || (name->Length && !name->Buffer)) return 0;
    int m=expr->Length/2, n=name->Length/2, last_dot=-1;
    if (!m || !n) return m==n;
    for (int i=0;i<n;i++) if (name->Buffer[i]=='.') last_dot=i;
    /* ponytail: O(pattern*name), O(pattern) memory; use a sparse automaton if long patterns matter. */
    unsigned char *memory=allocate(2*(m+1));
    if (!memory) {
#ifdef _WIN32
        RtlRaiseStatus((long)0xc0000017);
#else
        abort();
#endif
        return 0;
    }
    unsigned char *next=memory, *cur=memory+m+1;
    for (int i=n;i>=0;i--) {
        cur[m]=(i==n);
        WCHAR ch=i<n ? name->Buffer[i] : 0;
        if (ignore_case && i<n) ch=table ? table[ch] : uppercase(ch);
        for (int j=m-1;j>=0;j--) {
            WCHAR c=expr->Buffer[j];
            if (c=='*' || c=='<')
                cur[j]=cur[j+1] || (i<n && (c=='<' && i==last_dot ? next[j+1] : next[j]));
            else if (c=='>')
                cur[j]=(i==n || name->Buffer[i]=='.') ? cur[j+1] : next[j+1];
            else if (c=='"')
                cur[j]=i==n ? cur[j+1] : (name->Buffer[i]=='.' && next[j+1]);
            else
                cur[j]=i<n && (c=='?' || c==ch) && next[j+1];
        }
        unsigned char *swap=next; next=cur; cur=swap;
    }
    BOOLEAN result=next[0]; release(memory); return result;
}
#ifdef _WIN32
__declspec(dllimport) void *GetProcAddress(void *,const char *);
__declspec(dllimport) void *GetModuleHandleW(const WCHAR *);
static int equal(const char *a,const char *b) { while (*a && *a==*b) {a++;b++;} return *a==*b; }
void *CompatGetProcAddress(void *module,const char *name) {
    void *real=GetProcAddress(module,name);
    if (real) return real;
    if ((unsigned long long)name>65535 && equal(name,"RtlIsNameInExpression") &&
        module==GetModuleHandleW(L"ntdll.dll")) return (void *)sw_match;
    return real;
}
#endif
