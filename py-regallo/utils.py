import re
import json
import glob
import cfg
import pygraphviz as pgv
import numpy as np
from cfg.printer import FunctionString, Opts

from dashtable import data2rst
import matplotlib.patches as mpatches
from matplotlib import pyplot as plt

SEPARATOR = "/" # Should be the same as in cfgextractor in C++

#########################################################################
########################## HELPER FUNCTIONS ############################
#########################################################################

# Extracts first number from a string if there is any.
def extract_num_from_id(id_):
    res = re.findall(r'\d+', id_)
    if len(res) > 0:
        return int(res[0])
    return None

# Often Variable or BasicBlock names are of the form var_id/llvm_name
# or bb_id/llvm_name. This function extracts the id.
def extract_id(full_name):
    return full_name.split(SEPARATOR)[0]

# Checks if the given name is the name of proper (allocable) Variable
def is_varname(name):
    if name is None:
        return False
    return re.match('v[0-9]+', name) is not None

# Checks if the given name is the name of a BasicBlock.
def is_bbname(name):
    if name is None:
        return False
    return re.match('bb[0-9]+', name) is not None

# Checks if the given name is the name of a register
def is_regname(name):
    if name is None:
        return False
    return re.match('reg[0-9]+', name) is not None

def is_slotname(name):
    if name is None:
        return False
    return re.match('mem\(v[0-9]+\)', name) is not None

def slot(var):
    return "mem("+var.id+")"

# Reads all json files from the given directory and creates a Module
# from each. Returns a list of the Modules.
def modules_from_files(dir_path):
    modules = []
    for filename in glob.glob(dir_path+'*.json'):
        m = cfg.Module.from_file(filename)
        modules.append(m)

    return modules

#########################################################################
########################### GRAPH OPERATIONS ############################
#########################################################################

# DFS function that traverses basic blocks.
def dfs(bb, visited, **params):
    vpre = params.get("vpre", None)
    vpost = params.get("vpost", None)
    ef = params.get("ef", None)
    backwards = params.get("backwards", False)
    vstop = params.get("vstop", None) # id of bb at which, after processing,  dfs should stop

    # Mark as visited.
    visited.add(bb.id)

    # Call vertex function if exists.
    if vpre is not None:
        vpre(bb)

    # Maybe stop here.
    if vstop and bb.id == vstop.id:
        return

    neighbours = (bb.succs, bb.preds)[backwards]
    for n in neighbours.values():
        # Call edge function if exists.
        if ef is not None:
            ef((bb, n))
        if n.id not in visited:
           dfs(n, visited, **params) 

    if vpost is not None:
        vpost(bb)

# Returns list of basic blocks of the given function in postorder.
def postorder(f):
    bbs = []
    def vpost(bb):
        bbs.append(bb)

    dfs(f.entry_bblock, visited=set(), vpost=vpost)
    return bbs

# Returns list of basic blocks of the given function in reverse postorder.
# It guarantees that for each edge (a DOM> b), a will be before b
def reverse_postorder(f):
    bbs = postorder(f)
    return bbs[::-1]

# This function takes list of basic blocks, and assignes numbers to instructions in this order.
def number_instructions(bbs):
    n = 0
    num_to_instr = {}
    for bb in bbs:
        for instr in bb.instructions:
            instr.num = n
            num_to_instr[n] = instr
            n +=1

    return num_to_instr

#########################################################################
############################### REGISTERS ###############################
#########################################################################

# RegisterSet is a helper class for managing registers.
# It is made up of a set of free registers and a set of allocated registers.
# To return a free register it removes one from the set of free registers (if there are any)
# and adds it to the set of allocated ones (both in O(lg N)). If some register becomes free,
# it performs a reverse operation.
class RegisterSet:
    def __init__(self, count):
        self.count = count
        # A list of free registers ['reg_count', 'reg_{count-1}', ..., 'reg3', 'reg2', 'reg1']
        self.free = set(["reg"+str(i+1) for i in range(count)])
        self.occupied = set()

    # Returns id of one of free registers. If there are no free registers, returns None.
    def get_free(self):
        if len(self.free) == 0:
            return None
        x = self.free.pop()
        self.occupied.add(x)
        return x

    # Frees the given registers (makes it available for another allocation).
    def set_free(self, reg):
        assert reg in self.occupied
        self.occupied.remove(reg)
        self.free.add(reg)

    def occupy(self, reg):
        assert reg in self.free
        self.occupied.add(reg)
        self.free.remove(reg)

#########################################################################
############################### DRAWINGS ################################
#########################################################################

# Draws plot with provided intervals. Each interval is a line segment [iv.fr, iv.to],
# with Y coordinate equal to numerical sufix of corresponding variable id.
# to_file - name of the file where the plot should be saved. If None, the plot is shown
#                in the pop-up window.
def draw_intervals(intervals, regcount=0, to_file=None, figsize=None, with_subintervals=False, title="Lifetime intervals"):
    plt.figure(figsize=figsize)
    id_nums = []

    cmap = plt.get_cmap('gnuplot')
    colors = [cmap(i) for i in np.linspace(0, 0.8, regcount+1)]
    black = colors[0]
    reg_colors = {}

    if regcount:
        regset = RegisterSet(regcount)
        reg_colors = {reg: col for reg, col in zip(list(regset.free), colors[1:])}

    for (vid, ivlist) in intervals.iteritems():
        id_num = int(extract_num_from_id(vid))
        id_nums.append(id_num)
        
        for iv in ivlist:
            x = []
            y = []
            if with_subintervals:
                for sub in iv.subintervals:
                    # None at the end guarantees that line is not continuous all the time and
                    # there are holes in the plot in proper moments.
                    x.extend([sub.fr, sub.to, None])
                    y.extend([id_num, id_num, None])
            else:
                x.extend([iv.fr, iv.to, None])
                y.extend([id_num, id_num, None])
  
            color = black
            linestyle = 'solid'
            if regcount and is_regname(iv.alloc):
                color = reg_colors[iv.alloc]
            elif is_slotname(iv.alloc):
                linestyle = '--'

            plt.plot(x, y, color=color, linestyle=linestyle)

    plt.title(title)
    plt.xlabel('Instruction number')
    plt.ylabel('Variable id')
    plt.margins(0.05)

    #plt.legend(loc='best')
    #plt.yticks(id_nums)
    if to_file:
        plt.savefig(to_file)
    else:
        plt.show()
    plt.close()

# Takes dictionary of neighbours and draws corresponding
# graph saving it either as png or dot. It seems that the
# pictures are better if we save it in .dot and later
# execute 'dot -Tpng file.dot -o file.png'.
def draw_graph(neighs, filename, dot=True):
    A=pgv.AGraph()
    for v, nlist in neighs.iteritems():
        for n in nlist:
            A.add_edge(v.id, n.id)
    
    if filename.endswith('.dot'):
        A.write(filename)
    elif filename.endswith('.png'):
        A.layout()
        A.draw(filename)

#########################################################################
########################### COMPUTING RESULTS ###########################
#########################################################################

# A helper class for storing arguments for computing full results. 
# inputs - list of Functions or list of Modules
# regcounts - list of ints denoting number of registers.
# allocators - list of triples allocators.
# cost_calculators - list of CostCalculators.
class ResultCompSetting:
    def __init__(self, inputs, regcounts, allocators, cost_calculators):
        self.inputs = inputs
        self.regcounts = regcounts
        self.allocators = allocators
        self.cost_calculators = cost_calculators

    def allocator_names(self):
        return [al.name for al in self.allocators]

    def cost_calc_names(self):
        return [cc.name for cc in self.cost_calculators]


# For provided ResultSetting object, computes results for provided arguments returning
# list [(input_name, [(regcount, [(allocator_name, [(cost_name, RESULT)] )] )] )].
def compute_full_results(setting):
    results = []

    for inp in setting.inputs:
        # REGISTERS
        reg_results = []
        for regc in setting.regcounts:
            # ALLOCATORS
            alloc_results = []
            for al in setting.allocators:
                input_after_allocation = None
                if isinstance(inp, cfg.Function):
                    input_after_allocation = al.perform_full_register_allocation(inp, regc)
                elif isinstance(inp, cfg.Module):
                    input_after_allocation = al.perform_full_module_register_allocation(inp, regc)

                # COSTS 
                cost_results = []
                for cc in setting.cost_calculators:
                    res =  -1
                    if input_after_allocation:
                        if isinstance(inp, cfg.Function):
                            res = cc.function_diff(input_after_allocation, inp) # cost(g) - cost(f)
                        if isinstance(inp, cfg.Module):
                            res = cc.module_diff(input_after_allocation, inp)
                    
                    cost_results.append((cc.name, res))

                alloc_results.append((al.name, cost_results))

            reg_results.append((regc, alloc_results))

        results.append((inp.name, reg_results))

    return results


# Computes a table with span lists that we can print out to the
# console using dashtable.data2rst.
# d - results computed by compute_full_results
# setting - a ResultCompSetting object.
# We assume that d is correctly computed result table and per
# each function and regcount there is the same number of results.
def compute_result_table(d, setting):
    allocator_names = setting.allocator_names()
    cost_calc_names = setting.cost_calc_names()

    spans = [[[0,0],[0,1]]] # , [[1,0],[1,1]]]
    table = []

    # Zero row: Allocators
    row0 = ["", ""]
    col = 2
    for al in allocator_names:
        row0.append(al)
        for c in range(len(cost_calc_names)-1):
            row0.append("")

        # Don't add one-element spans.
        if len(cost_calc_names) > 1:
            span = [[0,col+el] for el in range(len(cost_calc_names))]
            col += len(cost_calc_names)
            spans.append(span)

    table.append(row0)


    # First row: Costs
    row1 = ["Input", "Registers"]
    for al in allocator_names:
        row1.extend(cost_calc_names)
    table.append(row1)

    # Remaining rows
    row = 2
    for fname, reg_results in d:
        regcount = len(reg_results)

        # Don't add one-element spans.
        if regcount > 1:
            span = [[row+el,0] for el in range(regcount)]
            spans.append(span)
            row += regcount

        first = True
        for reg, alloc_results in reg_results:
            rowN = [""]
            if first:
                rowN = [fname]
                first = False
            rowN.append(reg)

            for alname, cost_results in alloc_results:
                for c, res in cost_results:
                    if res == -1:
                        res = "Failed"
                    rowN.append(res)

            table.append(rowN)
    
    return table, spans

# Computes and prints to the output table with results provided as argument.
def compute_and_print_result_table(results, setting):
    table, spans = compute_result_table(results, setting)
    print(data2rst(table, spans=spans, use_headers=True))

# For given setting (with only one cost calculator allowed) and corresponding results,
# draws a separate plot (regcount -> sum of costs of each input) for every provided algorithm.
# (one image but different plots for each algorithm).
# It can be used when settings.inputs are Modules but it's sensible to draw it for one Module
# only because costs for multiple inputs are summed up.
def plot_reg_to_cost(results, settings, to_file=None, figsize=None):
    plots = {alname: {} for alname in settings.allocator_names()}
    regcounts = set()
    for (input_name, regs) in results:
        for (reg, allocators) in regs:
            regcounts.add(reg)
            for (alname, costs) in allocators:
                c = costs[0][1]
                if reg in plots[alname]:
                    if c == -1:
                        # -1 means failure, don't add
                        plots[alname][reg] = -1
                    elif plots[alname][reg] >= 0:
                        plots[alname][reg] += c
                else:
                    plots[alname][reg] = c

    cname = settings.cost_calc_names()[0]
   
    plt.figure(figsize=figsize)
    for alname, costs in plots.iteritems():
        x = sorted(costs.keys())
        y = [costs[reg] for reg in x]
        failures = len([val for val in y if val < 0])
        x = x[failures:]
        y = y[failures:]

        plt.plot(x, y, label=alname) # colors

    plt.legend(loc='upper right')
    plt.margins(0.05)
    plt.xticks(list(regcounts))
    plt.title("regcount - cost")
    plt.ylabel(cname)
    plt.xlabel("number of registers")
    if to_file:
        plt.savefig(to_file)
    else:
        plt.show()
    plt.close()
    

