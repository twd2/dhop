
from idautils import *
from idaapi import *
import idc


idc.Wait()

# TODO
fo = open('results/fun_output.txt', 'w')
ea = BeginEA()
fo.write(hex(ea) + '\n')
for funcea in Functions(SegStart(ea), SegEnd(ea)):
    functionName = GetFunctionName(funcea)
    fo.write(functionName + '\n')
fo.close()
idc.Exit(0)
