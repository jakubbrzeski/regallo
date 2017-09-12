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

    """
    res = bas.perform_register_allocation(g, 3)
    g.perform_full_analysis()
    resolve.insert_spill_code(g)
    res = bas.perform_register_allocation(g, 5, spilling=False)
    print "SUCCESS: ", res 
    print FunctionString(g, Opts(with_alloc=True, predecessors=True, successors=True))
    print "\n- - - - - - - - AFTER PHI ELIMINATION - - - - - - - - - - \n"    
    resolve.eliminate_phi(g, 5)
    g.perform_full_analysis()
    g.perform_liveness_analysis_with_alloc()
    if res:
        print FunctionString(g, Opts(with_alloc=True, predecessors=True, successors=True, reg_liveness=True, liveness_with_alloc=True, liveness=True, defs_uevs=True, reg_defs_uevs=True, defs_uevs_with_alloc=True))
        success = g.allocation_is_correct()
        print "SANITY CHECK:", success

        bb = g.bblocks["bb14"]
        for instr in bb.instructions:
            print instr.num, instr.reg_live_in, instr.reg_live_out


        print "\n"
        for instr in bb.instructions:
            print instr.num, instr.live_in_with_alloc, instr.live_out_with_alloc

    """
    #"""
    bas.perform_full_register_allocation(g, 5)
    g.perform_liveness_analysis_with_alloc()
    print FunctionString(g, Opts(with_alloc=True, liveness=True, liveness_with_alloc=True))
    success = g.allocation_is_correct()
    print "SANITY CHECK:", success
    #"""

else :
    flist = m.functions.values()

    bcc = BasicCostCalculator()
    src = SpillRatioCalculator()

    rcs = utils.ResultCompSetting(flist, [1, 3, 5], [bas, ext], [bcc, src])
    res = utils.compute_full_results(rcs)
    utils.print_result_table(res, rcs)

