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
parser.add_argument('-function', help="Name of the json file with CFG")

args = parser.parse_args()

with open(args.file) as f:
    module_json = json.load(f)

m = cfg.Module.from_json(module_json)
m.perform_full_analysis()
print "Functions in the module: ", ", ".join(m.functions.keys())

#f = m.functions[args.function]
#als = AdvLinearScan(f)
#ivs = als.compute_intervals()
#print FunctionPrinter(f)
#print IntervalsPrinter(ivs, Opts(intervals_advanced=True)).full()
#utils.draw_intervals(ivs, save_to_file="ivs.png", figsize=(10,10), with_subintervals=True)

#"""
allocators = [
            ("furthest first", BasicLinearScan, {}),
            ("current first", BasicLinearScan, {"spilling_strategy": BasicLinearScan.SpillingStrategy.CURRENT_FIRST}),
            ("less used first", BasicLinearScan, {"spilling_strategy": BasicLinearScan.SpillingStrategy.LESS_USED_FIRST})]

setting = utils.ResultCompSetting(
        functions = m.functions.values(),
        regcounts = [2, 4],
        allocators = allocators,
        cost_calculators = [BasicCostCalculator(), SpillRatioCalculator()])

res = utils.compute_full_results(setting)
utils.print_result_table(res, setting)
#"""
#utils.plot_reg_algorithm(res, setting, save_to_file="final.png")
