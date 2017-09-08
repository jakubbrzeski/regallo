import json
import argparse
import utils

import allocators.utils as alutils
from allocators.lscan.basic.spillers import CurrentFirst, LessUsedFirst
from allocators.lscan.basic import BasicLinearScan

from cost import BasicCostCalculator, SpillRatioCalculator

import cfg
import cfg.resolve as resolve
from cfg.cfgprinter import InstrString, FunctionString, IntervalsString, CostString, Opts

parser = argparse.ArgumentParser(description='Process json with CFG')
parser.add_argument('-file', help="Name of the json file with CFG")
parser.add_argument('-function', help="Name of the json file with CFG")

args = parser.parse_args()

with open(args.file) as f:
    module_json = json.load(f)

m = cfg.Module.from_json(module_json)
m.perform_full_analysis()
print "Functions in the module: ", ", ".join(m.functions.keys())
f = m.functions[args.function]
g = f.copy()


bcc = BasicCostCalculator()
bls = BasicLinearScan()
ivs = bls.compute_intervals(g)
print IntervalsString(ivs)


"""
print FunctionString(f)
bls = BasicLinearScan(name="furthest first")
blscf = BasicLinearScan(spiller=CurrentFirst(), name="current first")


ivs = bls.compute_intervals(f)
bls.allocate_registers(ivs, 2)
print IntervalsString(ivs)
resolve.insert_spill_code(f)
f.perform_full_analysis()
print FunctionString(f)
print CostString(f, bcc)
"""
"""
ivscf = blscf.compute_intervals(g)
blscf.allocate_registers(ivscf, 0)
print IntervalsString(ivscf)
utils.draw_intervals(ivscf, "before.png")

resolve.insert_spill_code(g)
g.perform_full_analysis()
print FunctionString(g)
print CostString(g, bcc)

ivscf = blscf.compute_intervals(g)
print IntervalsString(ivscf)
utils.draw_intervals(ivscf, "after.png")
success = blscf.allocate_registers(ivscf, 2, spilling=False)
print "Allocation: ", success

rcs = utils.ResultCompSetting([f], [2], [bls, blscf], [bcc])
res = utils.compute_full_results(rcs)
utils.print_result_table(res, rcs)
"""
