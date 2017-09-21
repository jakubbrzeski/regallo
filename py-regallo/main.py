import json
import argparse
import utils
import pprint


from allocators.lscan.basic.spillers import CurrentFirst, LessUsedFirst
from allocators.lscan.basic import BasicLinearScan
from allocators.lscan.extended import ExtendedLinearScan

from cost import MainCostCalculator, SpillInstructionsCounter

import cfg
import cfg.sanity as sanity
import cfg.resolve as resolve
import cfg.analysis as analysis
from cfg.printer import InstrString, FunctionString, IntervalsString, CostString, Opts

import allocators.graph as graph

parser = argparse.ArgumentParser(description='Process json with CFG')
parser.add_argument('-file', help="Name of the json file with CFG.")
parser.add_argument('-dir', help="Path to the directory with json files to read.")
parser.add_argument('-function', help="Name of the json file with CFG.")

args = parser.parse_args()

bas = BasicLinearScan(name="Furthest First")
bcf = BasicLinearScan(spiller=CurrentFirst(), name="Current First")
ext = ExtendedLinearScan()
mcc = MainCostCalculator()
sic = SpillInstructionsCounter()

if args.dir:
    modules = utils.modules_from_files(args.dir)
    for m in modules:
        analysis.perform_full_analysis(m)
        print m.name

    
    setting = utils.ResultCompSetting(
        inputs = modules,
        regcounts = [2],
        allocators = [bas],
        cost_calculators = [mcc])

    res = utils.compute_full_results(setting)
    utils.compute_and_print_result_table(res, setting)
  
    """
    # fft
    fft = modules[1] 
    setting = utils.ResultCompSetting(
        inputs = [fft],
        regcounts = range(2,10),
        allocators = [bas],
        cost_calculators = [mcc])

    res = utils.compute_full_results(setting)
    utils.compute_and_print_result_table(res, setting)
    utils.plot_reg_to_cost(res, setting, to_file="plot.png")
    """
