import json
import argparse
import cfg
import utils
import resolve
from lscan.basic import BasicLinearScan
from lscan.advanced import AdvLinearScan
from cost import BasicCostCalculator, SpillRatioCalculator
from cfgprinter import InstrString, FunctionString, IntervalsString, CostString, Opts

parser = argparse.ArgumentParser(description='Process json with CFG')
parser.add_argument('-file', help="Name of the json file with CFG")
parser.add_argument('-function', help="Name of the json file with CFG")

args = parser.parse_args()

with open(args.file) as f:
    module_json = json.load(f)

m = cfg.Module.from_json(module_json)
m.perform_full_analysis()
print "Functions in the module: ", ", ".join(m.functions.keys())
#f = m.functions[args.function]
#print FunctionString(f)

bls = BasicLinearScan(name="furthest first")
bls_cf = BasicLinearScan(spilling_strategy=BasicLinearScan.SpillingStrategy.CURRENT_FIRST, name="current first")

rcs = utils.ResultCompSetting(m.functions.values(), [1, 2, 3], [bls, bls_cf], [BasicCostCalculator()])
res = utils.compute_full_results(rcs)
utils.print_result_table(res, rcs)


"""
success = utils.full_register_allocation(f, bls, 5)
print "success = ", success
if success:
    print FunctionString(f, Opts(with_alloc=False, predecessors=True, successors=True))
"""
