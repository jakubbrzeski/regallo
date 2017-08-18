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
print cfgprinter.function_str(f, instr_nums=bls.num)
intervals = bls.compute_intervals(print_debug=1)
print cfgprinter.intervals_str(intervals)

bls.allocate_registers(intervals, 6)
utils.update_alloc(intervals)


print cfgprinter.function_str(f, instr_nums=bls.num)


"""
utils.draw_intervals(bls.intervals, "before.png")
print "\n"




print "Intervals:"
print cfgprinter.intervals_str(bls.intervals)
utils.draw_intervals(bls.intervals, "before.png")


print ""

print cfgprinter.function_str(f, 
        liveness=False, 
        dominance=False, 
        loop_depth=True, 
        allocation=allocation,
        live_vars=[], 
        instr_nums=bls.num)


print "Intervals:"
print cfgprinter.intervals_str(bls.intervals)
utils.draw_intervals(bls.intervals, "after.png")
"""


'''
for loop in f.loops:
    llvm_names = [bb.llvm_name for bb in loop.body]
    parent = "None"
    if loop.parent is not None:
        parent = loop.parent.header.llvm_name
    print loop.header.llvm_name, " -> ", loop.tail.llvm_name, "depth: ", loop.depth, "parent", parent
'''
