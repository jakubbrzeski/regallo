import json
import argparse
import utils

from allocators.lscan.basic.spillers import CurrentFirst, LessUsedFirst
from allocators.lscan.basic import BasicLinearScan
from allocators.lscan.extended import ExtendedLinearScan

from cost import MainCostCalculator, SpillInstructionsCounter

import cfg
import cfg.sanity as sanity
import cfg.resolve as resolve
import cfg.analysis as analysis
from cfg.printer import InstrString, FunctionString, IntervalsString, CostString, Opts

parser = argparse.ArgumentParser(description='Process json with CFG')
parser.add_argument('-file', help="Name of the json file with CFG")
parser.add_argument('-function', help="Name of the json file with CFG")

args = parser.parse_args()

with open(args.file) as f:
    module_json = json.load(f)

m = cfg.Module.from_json(module_json)
analysis.perform_full_analysis(m)
#print "Functions in the module: ", ", ".join(m.functions.keys())


bas = BasicLinearScan(name="Furthest First")
bcf = BasicLinearScan(spiller=CurrentFirst(), name="Current First")
ext = ExtendedLinearScan()

mcc = MainCostCalculator()
sic = SpillInstructionsCounter()
if args.function:
    f = m.functions[args.function]
    print f.vars
    print FunctionString(f)
    min_pressure = f.minimal_register_pressure()
    max_pressure = f.maximal_register_pressure()
    print "   maximal pressure: ", max_pressure
    print "   minimal pressure: ", min_pressure
    print "   reachable bblocks:", [bid for bid in f.bblocks.keys()]
    res = bas.perform_full_register_allocation(f, min_pressure)
    if res is None:
        print "allocation failed"
    else:
        print "allocation succeeded"
        print FunctionString(res, Opts(mark_non_ssa=True, liveness=True, with_alloc=True, predecessors=True))
        correct = sanity.allocation_is_correct(res)
        print "allocation is correct: ", correct
        #cost = sic.function_diff(res, f)
        #print "   spill instructions: ", cost
    
else :
    flist = m.functions.values()
    for f in flist:
        print "FUNCTION: ", f.name
        min_pressure = f.minimal_register_pressure()
        max_pressure = f.maximal_register_pressure()
        print "   maximal pressure: ", max_pressure
        print "   minimal pressure: ", min_pressure
        res = bas.perform_full_register_allocation(f, max_pressure)
        if res:
            print "   allocation success"
            ac = sanity.allocation_is_correct(res)
            print "   allocation correct: ", ac
            dfc = sanity.data_flow_is_correct(res, f)
            print "   data flow correct: ", dfc
            cost = sic.function_diff(res, f)
            print "   spill instructions: ", cost
        else:
            print "   allocation failed."
        print "\n"

#    setting = utils.ResultCompSetting(flist, [2], [bas, bcf], [mcc, sic])
#    res = utils.compute_full_results(setting)
#    utils.compute_and_print_result_table(res, setting)
