import json
import argparse
import cfg
import utils
import lscan
import cost
import phi
from cfgprinter import FunctionPrinter, IntervalsPrinter, CostPrinter, PrintOptions as Opts
from pprint import pprint

parser = argparse.ArgumentParser(description='Process json with CFG')
parser.add_argument('-filename', help="Name of the json file with CFG")
args = parser.parse_args()

with open(args.filename) as f:
    cfg_dict = json.load(f)

f = cfg.Function.from_json(cfg_dict[0])
f.perform_full_analysis()

options_full = Opts(predecessors=True, successors=True,
        uevs_defs=True, liveness=True, dominance=True, intervals_verbose=True,
        show_spilled=True)

print FunctionPrinter(f, options_full)

bls = lscan.BasicLinearScan(f)
intervals = bls.compute_intervals(print_debug=1)
print IntervalsPrinter(intervals).full()

#utils.draw_intervals(intervals, "before.png")
bls.allocate_registers(intervals, 2)
print IntervalsPrinter(intervals).full()

bls.insert_spill_code(intervals)
print FunctionPrinter(f)

print "AFTER PHI ELIMINATION"

phi.eliminate_phi(f)
f.perform_full_analysis()

print FunctionPrinter(f, Opts(nums=True, alloc_only=True))

#utils.draw_intervals(intervals, "after.png")
bcost = cost.BasicCostCalculator()
print CostPrinter(f, bcost).full()

#print "COST: ", bcost.function_cost(f)

