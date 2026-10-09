import ctypes, struct, os
cg = os.path.abspath(".venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")
buf = open(cg,"rb").read()
# EnergyTypes table at VA 0xe17e0. Need file offset: find section .rodata
import subprocess
out = subprocess.run(["readelf","-S",cg],capture_output=True,text=True).stdout
base = None
for line in out.splitlines():
    if ".rodata" in line and "PROGBITS" in line:
        parts = line.split()
        # find idx of PROGBITS then addr, off
        i = parts.index("PROGBITS")
        addr = int(parts[i+1],16); off = int(parts[i+2],16)
        base = (addr, off)
print("rodata addr/off:", base)
addr, off = base
fo = off + (0xe17e0 - addr)
vals = struct.unpack_from("<24H", buf, fo)
print("EnergyTypes[0..11] = ", vals)
