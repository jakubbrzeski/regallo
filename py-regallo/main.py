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
print "Functions in the module: ", ", ".join(m.functions.keys())


bas = BasicLinearScan(name="Furthest First")
bcf = BasicLinearScan(spiller=CurrentFirst(), name="Current First")
ext = ExtendedLinearScan()

mcc = MainCostCalculator()
sic = SpillInstructionsCounter()
if args.function:

    f = m.functions[args.function]
    print FunctionString(f, Opts(mark_non_ssa=True, liveness=True, predecessors=True))
    max_pressure = f.maximal_register_pressure()
    print "max pressure: ", max_pressure
    res = bas.perform_full_register_allocation(f, max_pressure)


    if res is None:
        print "allocation failed"
    else:
        print "allocation succeeded"
        cost = sic.function_diff(res, f)
        print "   spill instructions: ", cost

else :
    flist = m.functions.values()
    for f in flist:
        print "FUNCTION: ", f.name
        max_pressure = f.maximal_register_pressure()
        print "   maximal pressure: ", max_pressure
        res = bas.perform_full_register_allocation(f, max_pressure)
        if res:
            print "   allocation success"
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

