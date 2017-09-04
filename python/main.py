import json
import argparse
import cfg
import utils
from lscan.basic import BasicLinearScan
from lscan.advanced import AdvLinearScan
from cost import BasicCostCalculator, SpillRatioCalculator
from cfgprinter import FunctionPrinter, IntervalsPrinter, CostPrinter, PrintOptions as Opts

parser = argparse.ArgumentParser(description='Process json with CFG')
parser.add_argument('-file', help="Name of the json file with CFG")

args = parser.parse_args()

with open(args.file) as f:
    module_json = json.load(f)

m = cfg.Module.from_json(module_json)
m.perform_full_analysis()
gcd = m.functions['gcd']

print FunctionPrinter(gcd)
als = AdvLinearScan(gcd)
intervals = als.compute_intervals()

print IntervalsPrinter(intervals, Opts(intervals_advanced=True)).full()



#res = utils.compute_full_results(m.functions.values(), [0, 1, 2], [BasicLinearScan], [BasicCostCalculator(), SpillRatioCalculator()])
#utils.print_result_table(res, [BasicLinearScan.NAME], [BasicCostCalculator.NAME, SpillRatioCalculator.NAME])

