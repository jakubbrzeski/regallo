import re
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
def draw_intervals(intervals, save_to_file=None, figsize=None):
    vid_max = 0
    plt.figure(figsize=figsize)
    for (vid, ivlist) in intervals.iteritems():
        x = []
        y = []
        id_num = int(extract_num_from_id(vid))
        vid_max = id_num if id_num > vid_max else vid_max
        
        for iv in ivlist:
            # None at the end guarantees that line is not continuous all the time and
            # there are holes in the plot in proper moments.
            x.extend([iv.fr.num, iv.to.num, None])
            y.extend([id_num, id_num, None])

        plt.plot(x,y,label=str(vid))

    plt.title('Lifetime Intervals')
    plt.xlabel('Instruction numbers')
    plt.ylabel('Variable ids')
    plt.margins(0.05)
    plt.yticks(range(1, 1+vid_max))
    if save_to_file:
        plt.savefig(save_to_file)
    else:
        plt.show()
    plt.close()


def update_alloc(intervals):
    for iv in intervals.values():
        for siv in iv.subintervals:
            print iv.var.id, iv.reg
            siv.defn.alloc[iv.var.id] = iv.reg
            for use in siv.uses:
                use.alloc[iv.var.id] = iv.reg

# Returns mapping: functions -> allocators -> list of (calculator, cost)
# functions - list of Functions
# recounts - list of ints denoting number of registers
# allocators - list of allocator class names
# cost_calculators - list of CostCalculators
def compute_full_results(functions, regcounts, allocators, cost_calculators, analysis=False):
    results = {f.name: {regc: {alcls.NAME: {} for alcls in allocators} for regc in regcounts} for f in functions}
    for f in functions:
        for regc in regcounts:
            for alcls in allocators:
                g = f.copy()
                if analysis:
                    g.perform_full_analysis()
                
                al = alcls(g)
                al.full_register_allocation(regc)
                for cc in cost_calculators:
                    res = cc.function_cost(g)
                    results[f.name][regc][alcls.NAME][cc.NAME] = res

    return results
                
# Computes a table with span lists that we can print out to the
# console using dashtable.data2rst.
# d - dictionary of results {fname: {regcount: {allocator_name: {cost_calc_name: value}}}}
# allocator and cost_calc_names must be the same as in d.
def compute_result_table(d, allocator_names, cost_calc_names):
    spans = [[[0,0],[0,1]]]
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
    row1 = ["Functions", "Registers"]
    for al in allocator_names:
        row1.extend(cost_calc_names)
    table.append(row1)

    # Remaining rows
    row = 2
    for fname, regdict in d.iteritems():
        regcount = len(regdict)

        # Don't add one-element spans.
        if regcount > 1:
            span = [[row+el,0] for el in range(regcount)]
            spans.append(span)
            row += regcount

        first = True
        for reg, allocators in regdict.iteritems():
            rowN = [""]
            if first:
                rowN = [fname]
                first = False
            rowN.append(reg)
            for alname in allocator_names:
                costdict = allocators[alname]
                for cname in cost_calc_names:
                    val = costdict[cname]
                    rowN.append(val)

            table.append(rowN)
            
    return table, spans

def print_result_table(d, allocator_names, cost_calc_names):
    table, spans = compute_result_table(d, allocator_names, cost_calc_names)
    print(data2rst(table, spans=spans, use_headers=True))
