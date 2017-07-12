SEPARATOR = "/" # Should be the same as in cfgextractor in C++

class Colors:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    ENDC = '\033[0m'

def get_id_from_full_name(full_name):
    _id, _, _ = full_name.split(SEPARATOR)
    return _id


#########################################################################
############################### CFG MODEL ###############################
#########################################################################
class Variable:
    def __init__(self, instr, full_name):
        self.instr = instr # parent instruction
        # id is of the form 'v' + unique number e.g. "v128"
        self.id, self.llvm_id, gl = full_name.split(SEPARATOR)
        self.local = (False, True)[gl == "L"]

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id
        return False

    def __hash__(self):
        return int(self.id[1:]) # we omit "v" - first character of id

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return str(self.id)

    # Returns pretty string representation of this variable
    def pretty_str(self, kwargs):
        print_llvm_ids = kwargs.get("llvm_ids", False)
        if not self.local:
            res = "@" + self.id
        else:
            res = self.id
        if print_llvm_ids and len(self.llvm_id) > 0:
            res = res + "(" + self.llvm_id + ")"
        return res

class Instruction:
    def __init__(self, bb, instruction_json):
        self.bb = bb # parent basic block
        self.opname = instruction_json['opname']
        self.definition = Variable(self, instruction_json['def'])
        self.uses = [Variable(self, use) for use in instruction_json['use']]
        self.live_in = None
        self.live_out = None

    # Returns pretty string representation of this instruction
    def pretty_str(self, kwargs):
        live_vars = kwargs.get("live_vars", [])
        res = Colors.YELLOW + self.definition.pretty_str(kwargs) + " = " 
        res = res + Colors.RED + self.opname + Colors.YELLOW
        for use in self.uses:
            res = res + " " + use.pretty_str(kwargs)
        res = res + Colors.ENDC

        if len(live_vars) > 0:
            res = res + "  | " + Colors.GREEN
            assert self.live_in is not None
            live_ids = [v.id for v in list(self.live_in)]
            for i in range(len(live_vars)):
                if live_vars[i] in live_ids:
                    res = res + " (" + str(live_vars[i]) + ")"
            
        return res + Colors.ENDC

class BasicBlock:
    def __init__(self, func, bblock_json):
        self.parent = func
        self.id, self.llvm_id, _ = bblock_json['name'].split(SEPARATOR)
        self.instructions = [Instruction(self, instr_json) for instr_json in bblock_json['instructions']]
        self.preds = None
        self.succs = None

        self.instr_live_in = None
        self.instr_live_out = None

        self.defs = None
        self.uevs = None
        self.live_in = None
        self.live_out = None

        self.dominators = None

    # Lazily computes and returns a pair of variable sets (defs, uevs) for this basic block
    # defs - variables defined in the basic block
    # uevs - variables that are used before any redefinition
    # It doesn't take into account global variables.
    def get_defs_and_uevs(self):
        if self.defs is not None and self.uevs is not None:
            return self.defs, self.uevs

        defs = set()
        uevs = set()
        for instr in self.instructions:
            for use in instr.uses:
                if use not in defs and use.local:
                    uevs.add(use)
            
            defs.add(instr.definition)

        self.defs = defs
        self.uevs = uevs
        return self.defs, self.uevs

    # Lazily computes and returns two lists of Live-In and Live-Out
    # sets of subsequent instructions of this basic block.
    def perform_instr_liveness_analysis(self):
        current_live_set = self.live_in.copy()
        for instr in self.instructions:
            instr.live_in = current_live_set
            current_live_set -= {instr.definition}
            instr.live_out = current_live_set

        # reverse
        current_live_set = self.live_out.copy()
        for instr in self.instructions[::-1]:
            instr.live_out |= current_live_set
            current_live_set -= {instr.definition}
            instr.live_in |= current_live_set
            

    # Returns pretty string representation of this basic block
    def pretty_str(self, kwargs):
        print_llvm_ids = kwargs.get("llvm_ids", False)
        print_uev_def = kwargs.get("uev_def", True)
        print_liveness = kwargs.get("liveness", False)
        print_dominance = kwargs.get("dominance", False)

        res = self.id 
        if len(self.llvm_id) > 0:
            res = res + "("+self.llvm_id+")"

        for instr in self.instructions:
            res = res + "\n  > " + instr.pretty_str(kwargs)
        
        # successors
        res = res + "\n  SUCC: ["
        for i in range(len(self.succs)):
            if i:
                res = res + ", "
            res = res + self.succs[i].id
        res = res + "]"

        # dominators
        if print_dominance:
            assert self.dominators is not None
            dominators = list(self.dominators)
            res = res + "\n  DOM: ["
            for i in range(len(dominators)):
                if i:
                    res = res + ", "
                res = res + dominators[i].id
            res = res + "]"

        # upword-exposed vars and definitions
        if print_uev_def:
            defs, uevs = self.get_defs_and_uevs()
            defs, uevs = list(defs), list(uevs)
            # uevars
            res = res + "\n  UEV: ["
            for i in range(len(uevs)):
                if i:
                    res = res + ", "
                res = res + uevs[i].pretty_str(kwargs)
            res = res + "]"
            # definitions
            res = res + "\n  DEFS: ["
            for i in range(len(defs)):
                if i:
                    res = res + ", "
                res = res + defs[i].pretty_str(kwargs)
            res = res + "]"

        # live variables
        if print_liveness:
            assert self.live_in is not None and self.live_out is not None
            # live-in 
            live_in_list = list(self.live_in)
            res = res + "\n  LIVE-IN: ["
            for i in range(len(live_in_list)):
                if i:
                    res = res + ", "
                res = res + live_in_list[i].pretty_str(kwargs)
            res = res + "]"
            # live-out
            live_out_list = list(self.live_out)
            res = res + "\n  LIVE-OUT: ["
            for i in range(len(live_out_list)):
                if i:
                    res = res + ", "
                res = res + live_out_list[i].pretty_str(kwargs)
            res = res + "]"

        return res


class FunctionCFG:
    def __init__(self, function_json):
        self.name = function_json['name']
        entry_block_id = get_id_from_full_name(function_json['entry_block'])
        
        bblocks_json = function_json['bblocks']
        self.bb_list = [BasicBlock(self, bb) for bb in bblocks_json]
        self.bb_dict = {bb.id: bb for bb in self.bb_list} # {id -> BasicBlock}

        # Liveness sets
        self.bb_live_in = None
        self.bb_live_out = None
       
        # Set predecessors and successors
        for bbj in bblocks_json:
            _id = get_id_from_full_name(bbj['name'])

            preds_list = []
            if bbj['predecessors'] is not None:
                pred_ids = [get_id_from_full_name(fname) for fname in bbj['predecessors']]
                preds_list = [self.bb_dict[pred_id] for pred_id in pred_ids]

            succs_list = []
            if bbj['successors'] is not None:
                succ_ids = [get_id_from_full_name(fname) for fname in bbj['successors']]
                succs_list = [self.bb_dict[succ_id] for succ_id in succ_ids]

            self.bb_dict[_id].preds = preds_list
            self.bb_dict[_id].succs = succs_list
            

        self.entry_block = self.bb_dict[entry_block_id]

    # Performs liveness analysis - for each basic block and instruction computes 
    # live_in and live_out variable sets
    # Returns dictionaries live_in: {bb.id -> set of live-in vars} and live_out accordingly.
    #
    # ordered_bbs (optional) - a list of ids - the order of bblocks in which to perform
    #                          round robin algorithm, e.g. in reverse postorder.
    def perform_liveness_analysis(self, ordered_bbs = None):
        if ordered_bbs is None:
            ordered_bbs = self.bb_list

        live_in = {}
        live_out = {}

        # initialize sets
        for bb in ordered_bbs:
            bb.live_in = set()
            bb.live_out = set()

        change = True
        iterations = 0
        while change:
            iterations += 1
            change = False
            for bb in ordered_bbs:
                live_in_size, live_out_size = len(bb.live_in), len(bb.live_out)
                for succ in bb.succs:
                    # We add to current basic block's live-out set all 
                    # variables that are 'live in' in its successor.
                    bb.live_out |= succ.live_in

                # Live-in set of the basic block consists of all variables
                # that are upword-exposed or live-out but not defined in this block.
                defs, uevs = bb.get_defs_and_uevs() # sets
                bb.live_in = (uevs | (bb.live_out - defs))

                if len(bb.live_in) > live_in_size or len(bb.live_out) > live_out_size:
                    change = True

        for bb in ordered_bbs:
            bb.perform_instr_liveness_analysis() # updates liveness for each instr
            live_in[bb.id] = bb.live_in
            live_out[bb.id] = bb.live_out

        self.live_in = live_in
        self.live_out = live_out
        print "Liveness analysis done, #iterations = ", iterations
        return self.live_in, self.live_out

    # Performs dominance analysis on basic blocks of this function
    def perform_dominance_analysis(self, ordered_bbs = None):
        if ordered_bbs is None:
            ordered_bbs = self.bb_list

        for bb in ordered_bbs:
            bb.dominators = set({bb})

        change = True
        while change:
            change = False
        
            for bb in ordered_bbs:
                dominators_size = len(bb.dominators)
                preds_dominators = [pred.dominators for pred in bb.preds]
                if len(preds_dominators) > 0:
                    bb.dominators |= set.intersection(*preds_dominators)

                if len(bb.dominators) > dominators_size:
                    change = True

    # Returns pretty string representation of this function
    def pretty_str(self, **kwargs):
        print_bb_live_sets = kwargs.get("bb_live_sets", True)
        print_uev_def = kwargs.get("uev_def", True)

        res = "FUNCTION " + self.name
        for bb in self.bb_list:
            res = res + "\n" + bb.pretty_str(kwargs)
                       
        return res
    
class Module:
    def __init__(self, cfg_json):
        self.functions = [Function(f) for f in cfg_json]


#########################################################################
########################### GRAPH OPERATIONS ############################
#########################################################################

def visit_block(bb, postorder, rev_order = False, visited = set()):
    visited.add(bb.id)
    neighbours = (bb.successors, bb.predecessors)[rev_order]
    for neigh in neighbours:
        print " ", neigh.id
        if neigh.id not in visited:
            visit_block(neigh, postorder, rev_order, visited)

    postorder.append(bb.id)

def visit(fun, rev_order = False):
    postorder = []
    visit_block(fun.entry_block, postorder, rev_order)
    return postorder
    
