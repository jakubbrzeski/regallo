import json
import argparse
from copy import deepcopy
import cfg
import utils
from lscan.basic import BasicLinearScan
from cost import BasicCostCalculator, SpillRatioCalculator
import phi
from cfgprinter import FunctionPrinter, IntervalsPrinter, CostPrinter, PrintOptions as Opts
from pprint import pprint
from dashtable import data2rst

parser = argparse.ArgumentParser(description='Process json with CFG')
parser.add_argument('-filename', help="Name of the json file with CFG")
args = parser.parse_args()

with open(args.filename) as f:
    module_json = json.load(f)

m = cfg.Module.from_json(module_json)
m.perform_full_analysis()

res = utils.compute_full_results(m.functions.values(), [0, 1, 2], [BasicLinearScan], [BasicCostCalculator(), SpillRatioCalculator()])
utils.print_result_table(res, [BasicLinearScan.NAME], [BasicCostCalculator.NAME, SpillRatioCalculator.NAME])

