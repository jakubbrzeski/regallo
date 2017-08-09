import json
import argparse
import cfg
import utils
import lscan
import cfg_pretty_printer as cfgprinter
from pprint import pprint

parser = argparse.ArgumentParser(description='Process json with CFG')

parser.add_argument('-filename', help="Name of the json file with CFG")

args = parser.parse_args()

with open(args.filename) as f:
    cfg_dict = json.load(f)

#pprint (cfg_dict)
#pprint (cfg_dict[1])

f = cfg.Function.from_json(cfg_dict[0])
f.compute_defs_and_uevs()
f.perform_liveness_analysis()
f.perform_dominance_analysis()
f.perform_loop_analysis()



bls = lscan.BasicLinearScan(f)
bls.compute_intervals(print_debug=True)

print "\n"

print cfgprinter.function_str(f, 
        liveness=False, 
        dominance=False, 
        loop_depth=True, 
        live_vars=[], 
        instr_nums=bls.num)


print "Intervals:"
print cfgprinter.intervals_str(bls.intervals)






'''
for loop in f.loops:
    llvm_names = [bb.llvm_name for bb in loop.body]
    parent = "None"
    if loop.parent is not None:
        parent = loop.parent.header.llvm_name
    print loop.header.llvm_name, " -> ", loop.tail.llvm_name, "depth: ", loop.depth, "parent", parent
'''
