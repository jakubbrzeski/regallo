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
from cfg.printer import BBString, InstrString, FunctionString, IntervalsString, CostString, Opts

import allocators.graph as graph
from allocators.graph import BasicGraphColoringAllocator
from allocators.graph.spillers import BeladySpiller

parser = argparse.ArgumentParser(description='Process json with CFG')
parser.add_argument('-file', help="Name of the json file with CFG.")
parser.add_argument('-dir', help="Path to the directory with json files to read.")
parser.add_argument('-function', help="Name of the json file with CFG.")

args = parser.parse_args()

bas = BasicLinearScan(name="Furthest First")
bcf = BasicLinearScan(spiller=CurrentFirst(), name="Current First")
ext = ExtendedLinearScan()
bgca = BasicGraphColoringAllocator()

mcc = MainCostCalculator()
sic = SpillInstructionsCounter()

if args.file:
    
    m = cfg.Module.from_file(args.file)
#    analysis.perform_full_analysis(m)


    """
    setting = utils.ResultCompSetting(
        inputs = m.functions.values(),
        regcounts = [6, 7, 8],
        allocators = [bgca],
        cost_calculators = [mcc])


    res = utils.compute_full_results(setting)
    utils.compute_and_print_result_table(res, setting)
    """

    #name = "LZ4_sizeofStreamState"
    #name = "LZ4_compress_fast_continue"
    name = "LZ4_compress_forceExtDict"
    f = m.functions[name]
    analysis.perform_full_analysis(f)
    #for f in m.functions.values():
    print "FUNCTION", f.name
    print "min / max pressure: ", f.minimal_register_pressure(), f.maximal_register_pressure()
#    print FunctionString(f, Opts(successors=True, liveness=True, predecessors=True, dominators=True))
   
    """
    print BBString(f.entry_bblock, Opts(successors=True, liveness=True, predecessors=True, dominance=True))
    print BBString(f.bblocks["bb1184"], Opts(successors=True, liveness=True, predecessors=True, dominance=True))
    print BBString(f.bblocks["bb1181"], Opts(successors=True, liveness=True, predecessors=True, dominance=True))
    print BBString(f.bblocks["bb1177"], Opts(successors=True, liveness=True, predecessors=True, dominance=True))
    print BBString(f.bblocks["bb1194"], Opts(successors=True, liveness=True, predecessors=True, dominance=True))
    print BBString(f.bblocks["bb1176"], Opts(successors=True, liveness=True, predecessors=True, dominance=True))
    print BBString(f.bblocks["bb1195"], Opts(successors=True, liveness=True, predecessors=True, dominance=True))
    g = bgca.perform_full_register_allocation(f, 20)
    if g:
        print "SUCCESS"
        #print FunctionString(g, Opts(successors=True, liveness=True))
        print "max pressure: ", g.maximal_register_pressure()
    else:
        print "FAILURE"

    print "\n"
    """    

if args.dir:
    modules = utils.modules_from_files(args.dir)
    for m in modules:
        analysis.perform_full_analysis(m)
        print "START WITH", m.name, m.minimal_register_pressure(), m.maximal_register_pressure()

        setting = utils.ResultCompSetting(
            inputs = [m],
            regcounts = [20, 21, 22, 23, 24, 25], #range(modules[0].minimal_register_pressure(), modules[0].maximal_register_pressure()+1),
            allocators = [bgca, bas, ext],
            cost_calculators = [mcc])

        res = utils.compute_full_results(setting)
        utils.compute_and_print_result_table(res, setting)
        utils.plot_reg_to_cost(res, setting, to_file=m.name)
    
    #res = utils.compute_full_results(setting)
    #utils.compute_and_print_result_table(res, setting)

