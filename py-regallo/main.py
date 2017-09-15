import json
import argparse
import utils

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
    print FunctionString(f, Opts(predecessors=True, successors=True, liveness=True))
    print "-- -- -- -- -- -- -- --"

    res = bas.perform_full_register_allocation(f, 3)
    if res is None:
        print "allocation failed"
    else:
        print FunctionString(res, Opts(predecessors=True, successors=True, liveness=True))
        print "allocation correct:", res.allocation_is_correct()

else :
    flist = m.functions.values()

    bcc = BasicCostCalculator()
    src = SpillRatioCalculator()

    rcs = utils.ResultCompSetting(flist, [3, 5, 7], [bas], [bcc])
    res = utils.compute_full_results(rcs)
    utils.print_result_table(res, rcs)

