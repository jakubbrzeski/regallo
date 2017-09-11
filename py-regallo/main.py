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


bas = BasicLinearScan()
ext = ExtendedLinearScan()

if args.function:

    f = m.functions[args.function]
    f.compute_defs_and_uevs_with_alloc()
    #for bb in f.bblocks.values():
    #    print bb.llvm_name, bb.defs_with_alloc, bb.uevs_with_alloc
    print FunctionString(f, Opts(defs_uevs_with_alloc=True))
   
    bas.perform_full_register_allocation(f, 2)
    print f.perform_liveness_analysis_with_alloc()
    print f.perform_liveness_analysis()
    print FunctionString(f, Opts(defs_uevs=True, liveness=True, liveness_with_alloc=True))


else :
    flist = m.functions.values()

    bcc = BasicCostCalculator()
    src = SpillRatioCalculator()

    rcs = utils.ResultCompSetting(flist, [1, 3, 5], [bas, ext], [bcc, src])
    res = utils.compute_full_results(rcs)
    utils.print_result_table(res, rcs)

