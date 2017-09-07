import json
import argparse
import cfg
import utils
import resolve
from lscan.basic import BasicLinearScan
from lscan.advanced import AdvLinearScan
from cost import BasicCostCalculator, SpillRatioCalculator
from cfgprinter import InstrPrinter, FunctionPrinter, IntervalsPrinter, CostPrinter, PrintOptions as Opts

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
print FunctionPrinter(f)

bls = BasicLinearScan()
success = utils.full_register_allocation(f, bls, 5)
print "success = ", success
if success:
    print FunctionPrinter(f, Opts(with_alloc=True))
