import re
from cfgprinter import FunctionPrinter, PrintOptions as Opts
import resolve
from dashtable import data2rst
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

def scratch_reg():
    return "reg0"

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
        self.allocated = set()

    # Returns id of one of free registers. If there are no free registers, returns None.
    def get_free(self):
        if len(self.free) == 0:
            return None
        x = self.free.pop()
        self.allocated.add(x)
        return x

    # Frees the given registers (makes it available for another allocation).
    def set_free(self, reg):
        assert reg in self.allocated
        self.allocated.remove(reg)
        self.free.add(reg)


# Draws plot with provided intervals. Each interval is a line segment [iv.fr, iv.to],
# with Y coordinate equal to numerical sufix of corresponding variable id.
# save_to_file - name of the file where the plot should be saved. If None, the plot is shown
#                in the pop-up window.
def draw_intervals(intervals, save_to_file=None, figsize=None, with_subintervals=False):
    plt.figure(figsize=figsize)
    id_nums = []
    for (vid, ivlist) in intervals.iteritems():
        x = []
        y = []
        id_num = int(extract_num_from_id(vid))
        id_nums.append(id_num)
        
        for iv in ivlist:
            if with_subintervals:
                for sub in iv.subintervals:
                    # None at the end guarantees that line is not continuous all the time and
                    # there are holes in the plot in proper moments.
                    x.extend([sub.fr, sub.to, None])
                    y.extend([id_num, id_num, None])
            else:
                x.extend([iv.fr, iv.to, None])
                y.extend([id_num, id_num, None])
        
        plt.plot(x,y,label=str(vid))

    plt.title('Lifetime Intervals')
    plt.xlabel('Instruction numbers')
    plt.ylabel('Variable ids')
    plt.margins(0.05)
#    plt.yticks(id_nums)
    if save_to_file:
        plt.savefig(save_to_file)
    else:
        plt.show()
    plt.close()


# A helper class for passing arguments for function
# compute_full_results.
class AllocatorWrap:
    def __init__(self, name, alcls, **kwargs):
        self.name = name
        self.cls = alcls
        self.kwargs = kwargs

# A helper class for storing arguments for computing full results. 
# functions - list of Functions.
# regcounts - list of ints denoting number of registers.
# allocators - list of triples (name, allocator_class, **kwargs)
# cost_calculators - list of CostCalculators
class ResultCompSetting:
    def __init__(self, functions, regcounts, allocators, cost_calculators):
        self.functions = functions
        self.regcounts = regcounts
        self.allocators = allocators
        self.cost_calculators = cost_calculators

    def allocator_names(self):
        return [name for (name, _, _) in self.allocators]

    def cost_calc_names(self):
        return [cc.NAME for cc in self.cost_calculators]


# Returns mapping: list [(function_name, [(regcount, [(allocator_name, [(cost_name, RESULT)] )] )] )]
# setting - a ResultCompSetting object.
# analysis - whether to do full analysis for each function.
def compute_full_results(setting, analysis=False):
    results = []

    if analysis:
        for f in setting.functions:
            f.perform_full_analysis()

    for f in setting.functions:
        # REGISTERS
        reg_results = []
        for regc in setting.regcounts:

            # ALLOCATORS
            alloc_results = []
            for (name, cls, kwargs) in setting.allocators:
                g = f.copy()

                al = cls(g, **kwargs)
                al.full_register_allocation(regc)

                # COSTS 
                cost_results = []
                for cc in setting.cost_calculators:
                    res = cc.function_cost(g)
                    cost_results.append((cc.NAME, res))

                alloc_results.append((name, cost_results))

            reg_results.append((regc, alloc_results))

        results.append((f.name, reg_results))

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

    """
    row00 = ["", "", "Algorithms & Costs"]
    span = [ [0, 2+col] for col in range(len(allocator_names)*len(cost_calc_names))]
    row00.extend(["" for _ in span[1:]])
    table.append(row00)
    spans.append(span)
    """

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
    row1 = ["Functions", "Registers"]
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
                    rowN.append(res)

            table.append(rowN)
    
    return table, spans

def print_result_table(d, setting):
    table, spans = compute_result_table(d, setting)
    print(data2rst(table, spans=spans, use_headers=True))


# For given function and cost calculator, draws
# a plot (regcount -> result) for each algorithm
# (i.e. one drawing but separate plots for each algorithm).
# We assume that results contain numbers only for one function and cost calculator.
def plot_reg_algorithm(results, setting, save_to_file=None, figsize=None):
    assert len(results) == 1
    d = {alname: [] for alname in setting.allocator_names()}
    f, reg_results = results[0]

    cname = setting.cost_calc_names()[0]
    regcounts = [rc for (rc, _) in reg_results]

    for regcount, alloc_results in reg_results:
        for (alname, cost_results) in alloc_results:
            assert len(cost_results) == 1
            cname, cost = cost_results[0]
            d[alname].append((regcount,cost))


    plt.figure(figsize=figsize)
    for alname, values in d.iteritems():
        x = [rc for (rc, _) in values]
        y = [val for (_, val) in values]

        plt.plot(x, y, label=alname) # colors

    plt.legend(loc='upper left')
    plt.margins(0.05)
    plt.xticks(regcounts)
    plt.title("Results")
    plt.ylabel("cost")
    plt.xlabel("number of #registers")
    if save_to_file:
        plt.savefig(save_to_file)
    else:
        plt.show()
    plt.close()


def full_register_allocation(f, allocator, regcount):
    first_phase_regcount = regcount
    while (first_phase_regcount >= 0):
        allocator.full_allocation(f, first_phase_regcount)
        resolve.insert_spill_code(f)
        f.perform_full_analysis()

        success = allocator.full_allocation(f, regcount, spilling=False)
        if success:
            #print FunctionPrinter(f)
            resolve.eliminate_phi(f, regcount)
            f.perform_full_analysis()
            return True

        first_phase_regcount -= 1

    return False

