import json
import argparse
import utils
import pprint


import allocators.lscan.basic.spillers as bspillers 
import allocators.lscan.extended.spillers as extspillers 
from allocators.lscan.basic import BasicLinearScan
from allocators.lscan.extended import ExtendedLinearScan

from cost import MainCostCalculator, SpillInstructionsCounter

import cfg
import cfg.sanity as sanity
import cfg.resolve as resolve
import cfg.analysis as analysis
from cfg.printer import BBString, InstrString, FunctionString, IntervalsString, CostString, Opts

import allocators.graph as graph
from allocators.graph import BasicGraphColoringAllocator
from allocators.graph.spillers import BeladySpiller

parser = argparse.ArgumentParser(description='Process json with CFG')
parser.add_argument('-file', help="Name of the json file with CFG.")
parser.add_argument('-dir', help="Path to the directory with json files to read.")
parser.add_argument('-function', help="Name of the json file with CFG.")

args = parser.parse_args()

bas = BasicLinearScan(name = "Furthest End First")
bcf = BasicLinearScan(spiller=bspillers.CurrentFirst(), name="Current First")
bnu = BasicLinearScan(spiller=bspillers.FurthestNextUseFirst(), name="Basic Linear Scan")
blu = BasicLinearScan(spiller=bspillers.LessUsedFirst(), name="Less Used First")

ext = ExtendedLinearScan(name="Furthext First")
extnu = ExtendedLinearScan(spiller=extspillers.FurthestNextUseFirst(), name="Furthext Next Use First")
bgca = BasicGraphColoringAllocator(name="Graph Coloring")

mcc = MainCostCalculator()
sic = SpillInstructionsCounter()

if args.file:
    
    m = cfg.Module.from_file(args.file)
    analysis.perform_full_analysis(m)
   
    setting = utils.ResultCompSetting(
            inputs = [m],
            regcounts = range(m.minimal_register_pressure(), m.maximal_register_pressure()+1),
            allocators = [ext, extnu],
            cost_calculators = [mcc, sic])

    res = utils.compute_full_results(setting)
    utils.compute_and_print_result_table(res, setting)
    utils.plot_reg_to_cost(res, setting, cost_calc_index=0, to_file="1", title=m.name)
    utils.plot_reg_to_cost(res, setting, cost_calc_index=1, to_file="2", title=m.name)
    

if args.dir:
    modules = utils.modules_from_files(args.dir)
    for m in modules:
        analysis.perform_full_analysis(m)
        print m.name, m.minimal_register_pressure(), m.maximal_register_pressure(), m.instr_count()

        
        setting = utils.ResultCompSetting(
            inputs = [m],
            regcounts = range(m.minimal_register_pressure(), m.maximal_register_pressure()+1),
            allocators = [bgca, bnu, extnu],
            cost_calculators = [mcc, sic])

        res = utils.compute_full_results(setting)
        utils.compute_and_print_result_table(res, setting)
        utils.plot_reg_to_cost(res, setting, cost_calc_index=0, to_file=m.name+"MainCost", title=m.name)
        utils.plot_reg_to_cost(res, setting, cost_calc_index=1, to_file=m.name+"SpillCode", title=m.name)
        

    #res = utils.compute_full_results(setting)
    #utils.compute_and_print_result_table(res, setting)

