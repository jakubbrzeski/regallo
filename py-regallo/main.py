import json
import argparse
import utils

import allocators.utils as alutils
from allocators.lscan.basic.spillers import CurrentFirst, LessUsedFirst
from allocators.lscan.basic import BasicLinearScan
from allocators.lscan.extended import ExtendedLinearScan

from cost import BasicCostCalculator, SpillRatioCalculator

import cfg
import cfg.resolve as resolve
from cfg.printer import InstrString, FunctionString, IntervalsString, CostString, Opts

parser = argparse.ArgumentParser(description='Process json with CFG')
parser.add_argument('-file', help="Name of the json file with CFG")
parser.add_argument('-function', help="Name of the json file with CFG")

args = parser.parse_args()

with open(args.file) as f:
    module_json = json.load(f)

m = cfg.Module.from_json(module_json)
m.perform_full_analysis()
print "Functions in the module: ", ", ".join(m.functions.keys())


bas = BasicLinearScan(spiller=CurrentFirst())
ext = ExtendedLinearScan()

if args.function:

    f = m.functions[args.function]
    g = f.copy()

    print FunctionString(g, Opts(liveness=True, liveness_with_alloc=True))
    print f.bblocks["bb1"].live_in_with_alloc
    print f.bblocks["bb2"].live_in_with_alloc
    print f.bblocks["bb3"].live_in_with_alloc

    bas.perform_full_register_allocation(g, 2)
    g.perform_liveness_analysis()
    print FunctionString(g, Opts(with_alloc=True, liveness=True, liveness_with_alloc=True))
    success = g.allocation_is_correct()
    print "SANITY CHECK:", success

else :
    flist = m.functions.values()

    bcc = BasicCostCalculator()
    src = SpillRatioCalculator()

    rcs = utils.ResultCompSetting(flist, [3, 5, 7], [bas], [bcc])
    res = utils.compute_full_results(rcs)
    utils.print_result_table(res, rcs)

