import json
import argparse
import cfg
from pprint import pprint

parser = argparse.ArgumentParser(description='Process json with CFG')

parser.add_argument('-filename', help="Name of the json file with CFG")

args = parser.parse_args()

with open(args.filename) as f:
    cfg_dict = json.load(f)

#pprint (cfg_dict)
#pprint (cfg_dict[1])

f = cfg.FunctionCFG(cfg_dict[0])
f.perform_liveness_analysis()
f.perform_dominance_analysis()
print f.pretty_str(liveness=True, dominance=True, live_vars=["v1", "v12"], llvm_ids=True)
#print f.entry_block

'''
live_in, live_out = f.compute_bb_liveness()
print "live-in:"
pprint (live_in)
print "live-out:"
pprint (live_out)
'''

