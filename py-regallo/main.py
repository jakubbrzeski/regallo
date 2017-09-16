import json
import argparse
import utils

from allocators.lscan.basic.spillers import CurrentFirst, LessUsedFirst
from allocators.lscan.basic import BasicLinearScan
from allocators.lscan.extended import ExtendedLinearScan

from cost import MainCostCalculator, SpillInstructionsCounter

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


bas = BasicLinearScan(name="Furthest First")
bcf = BasicLinearScan(spiller=CurrentFirst(), name="Current First")
ext = ExtendedLinearScan()

mcc = MainCostCalculator()
sic = SpillInstructionsCounter()
if args.function:

    f = m.functions[args.function]

    res = bas.perform_full_register_allocation(f, 2)
    if res is None:
        print "allocation failed"
    else:
        print "allocation correct:", res.allocation_is_correct()
        print sic.function_diff(res, f)
        print CostString(res, sic)

else :
    flist = m.functions.values()


    setting = utils.ResultCompSetting(flist, [2], [bas, bcf], [mcc, sic])
    res = utils.compute_full_results(setting)
    utils.compute_and_print_result_table(res, setting)

