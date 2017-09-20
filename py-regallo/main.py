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
parser.add_argument('-file', help="Name of the json file with CFG")
parser.add_argument('-function', help="Name of the json file with CFG")

args = parser.parse_args()

with open(args.file) as f:
    module_json = json.load(f)

m = cfg.Module.from_json(module_json)
analysis.perform_full_analysis(m)

bas = BasicLinearScan(name="Furthest First")
bcf = BasicLinearScan(spiller=CurrentFirst(), name="Current First")
ext = ExtendedLinearScan()

mcc = MainCostCalculator()
sic = SpillInstructionsCounter()
if args.function:
    f = m.functions[args.function]
    print FunctionString(f)

    neighs = graph.build_interference_graph(f)
    utils.draw_graph(neighs, 'graph.dot')
    chordal = sanity.is_chordal(neighs)
    print "IS CHORDAL: ", chordal

 
else:
    setting = utils.ResultCompSetting(
        functions = m.functions.values(), # We take all the functions from the module
        regcounts = range(1, 20), 
        allocators = [bas, bcf], 
        cost_calculators = [sic])

    res = utils.compute_full_results(setting)
    utils.plot_reg_to_cost(res, setting)
    """
    flist = m.functions.values()
    for f in flist:
        print "FUNCTION: ", f.name
        min_pressure = f.minimal_register_pressure()
        max_pressure = f.maximal_register_pressure()
        print "   maximal pressure: ", max_pressure
        print "   minimal pressure: ", min_pressure
        res = bas.perform_full_register_allocation(f, 2)
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
    """
#    setting = utils.ResultCompSetting(flist, [2], [bas, bcf], [mcc, sic])
#    res = utils.compute_full_results(setting)
#    utils.compute_and_print_result_table(res, setting)
