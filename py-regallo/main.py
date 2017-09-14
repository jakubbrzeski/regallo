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

    print FunctionString(g, Opts(predecessors=True, successors=True))
    print "\n - - - - - - - - - - - - - - - - - - - - - - - - - \n"
    success = bas.perform_register_allocation(g, 0)
    resolve.insert_spill_code(g)
    g.perform_full_analysis()
    print success
    print FunctionString(g, Opts(predecessors=True, successors=True, liveness=True, with_alloc=True))

    #success = g.allocation_is_correct()
    #print "SANITY CHECK:", success

else :
    flist = m.functions.values()

    bcc = BasicCostCalculator()
    src = SpillRatioCalculator()

    rcs = utils.ResultCompSetting(flist, [3, 5, 7], [bas], [bcc])
    res = utils.compute_full_results(rcs)
    utils.print_result_table(res, rcs)

