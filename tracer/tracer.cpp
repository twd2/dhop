// ref: https://github.com/wapiflapi/villoc/blob/master/tracers/pintool/pintool.cpp

#include <iostream>
#include <fstream>
#include "pin.H"

#if defined(TARGET_MAC)
#define MALLOC "_malloc"
#define CALLOC "_calloc"
#define REALLOC "_realloc"
#define FREE "_free"
#else
#define MALLOC "malloc"
#define CALLOC "calloc"
#define REALLOC "realloc"
#define FREE "free"
#endif

#define TYPE_READY    0
#define TYPE_PID      1
#define TYPE_MALLOC   2
#define TYPE_CALLOC   3
#define TYPE_REALLOC  4
#define TYPE_FREE     5
#define TYPE_EXIT     6

ofstream output_file;

typedef struct
{
  size_t type;
  size_t arg1, arg2;
  size_t ret;
} packet_t;

static packet_t packet;
static size_t last_pc;

int mcount = 0;

static inline void send_packet(packet_t *packet)
{
  output_file.write((char *)packet, sizeof(packet_t));
}

VOID before_malloc(ADDRINT pc, ADDRINT size)
{
    last_pc = pc;
    packet.type = TYPE_MALLOC;
    packet.arg1 = size;
    packet.arg2 = 0;
    ++mcount;
    packet.ret = -1;
    send_packet(&packet);
}

VOID after_malloc(ADDRINT ret)
{
    packet.ret = ret;
    send_packet(&packet);
}

VOID before_calloc(ADDRINT pc, ADDRINT num, ADDRINT size)
{
    last_pc = pc;
    packet.type = TYPE_CALLOC;
    packet.arg1 = num;
    packet.arg2 = size;
    ++mcount;
    packet.ret = -1;
    send_packet(&packet);
}

VOID after_calloc(ADDRINT ret)
{
    packet.ret = ret;
    send_packet(&packet);
}

VOID before_realloc(ADDRINT pc, ADDRINT ptr, ADDRINT size)
{
    last_pc = pc;
    packet.type = TYPE_REALLOC;
    packet.arg1 = ptr;
    packet.arg2 = size;
    ++mcount;
    packet.ret = -1;
    send_packet(&packet);
}

VOID after_realloc(ADDRINT ret)
{
    packet.ret = ret;
    send_packet(&packet);
}

VOID before_free(ADDRINT pc, ADDRINT ptr)
{
    last_pc = pc;
    packet.type = TYPE_FREE;
    packet.arg1 = ptr;
    packet.arg2 = 0;
    ++mcount;
    packet.ret = -1;
    send_packet(&packet);
}

VOID after_free()
{
    packet.ret = 0;
    send_packet(&packet);
}

VOID instrument_image(IMG img, VOID *v)
{
    {
        RTN malloc_rtn = RTN_FindByName(img, MALLOC);
        if (RTN_Valid(malloc_rtn))
        {
            RTN_Open(malloc_rtn);
            RTN_InsertCall(malloc_rtn, IPOINT_BEFORE, (AFUNPTR)before_malloc,
                           IARG_RETURN_IP,
                           IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
                           IARG_END);
            RTN_InsertCall(malloc_rtn, IPOINT_AFTER, (AFUNPTR)after_malloc,
                           IARG_FUNCRET_EXITPOINT_VALUE, IARG_END);
            RTN_Close(malloc_rtn);
        }
    }

    {
        RTN calloc_rtn = RTN_FindByName(img, CALLOC);
        if (RTN_Valid(calloc_rtn))
        {
            RTN_Open(calloc_rtn);
            RTN_InsertCall(calloc_rtn, IPOINT_BEFORE, (AFUNPTR)before_calloc,
                           IARG_RETURN_IP,
                           IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
                           IARG_FUNCARG_ENTRYPOINT_VALUE, 1,
                           IARG_END);
            RTN_InsertCall(calloc_rtn, IPOINT_AFTER, (AFUNPTR)after_calloc,
                           IARG_FUNCRET_EXITPOINT_VALUE, IARG_END);

            RTN_Close(calloc_rtn);
        }
    }

    {
        cout << "finding realloc" << endl;
        RTN realloc_rtn = RTN_FindByName(img, REALLOC);
        if (RTN_Valid(realloc_rtn))
        {
            cout << "found" << endl;
            RTN_Open(realloc_rtn);
            RTN_InsertCall(realloc_rtn, IPOINT_BEFORE, (AFUNPTR)before_realloc,
                           IARG_RETURN_IP,
                           IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
                           IARG_FUNCARG_ENTRYPOINT_VALUE, 1,
                           IARG_END);
            RTN_InsertCall(realloc_rtn, IPOINT_AFTER, (AFUNPTR)after_realloc,
                           IARG_FUNCRET_EXITPOINT_VALUE, IARG_END);
            RTN_Close(realloc_rtn);
        }
    }

    {
        RTN free_rtn = RTN_FindByName(img, FREE);
        if (RTN_Valid(free_rtn))
        {
            RTN_Open(free_rtn);
            RTN_InsertCall(free_rtn, IPOINT_BEFORE, (AFUNPTR)before_free,
                           IARG_RETURN_IP,
                           IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
                           IARG_END);
            RTN_InsertCall(free_rtn, IPOINT_AFTER, (AFUNPTR)after_free,
                           IARG_END);
            RTN_Close(free_rtn);
        }
    }
}

KNOB<string> KnobOutputFile(KNOB_MODE_WRITEONCE, "pintool",
    "o", "tracer.out", "specify output file name");

VOID fin(INT32 code, VOID *v)
{
    cout << mcount << endl;
    output_file.close();
}

INT32 Usage()
{
    cerr << "This tool traces the program." << endl;
    cerr << KNOB_BASE::StringKnobSummary() << endl;
    return -1;
}

int main(int argc, char *argv[])
{
    PIN_InitSymbols();
    if (PIN_Init(argc, argv)) return Usage();
    output_file.open(KnobOutputFile.Value().c_str(), ofstream::out | ofstream::binary);
    IMG_AddInstrumentFunction(instrument_image, 0);
    PIN_AddFiniFunction(fin, 0);
    PIN_StartProgram(); // never return
    return 0;
}
