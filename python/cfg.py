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

# Variable names are of the form id/llvm_id/{L,G}. The llvm_id may be empty.
class Variable:
    def __init__(self, name, function):
        # The FunctionCFG we operate in
        self.f = function

        # The same variable may be used by many instructions, so we keep record
        # of them in dictionary: {instruction-id: Instruction}.
        self.instructions = {}

        vinfo = name.split(SEPARATOR)
        self.id = vinfo[0]
        
        self.llvm_id = None
        if len(vinfo) > 1 and vinfo[1] != '':
            self.llvm_id = vinfo[1]

        self.local = True
        if len(vinfo) > 2 and vinfo[2] == 'G':
            self.local = False

    # Adds the given Instruction to this Variable's record if it's not already there.
    # Returns True if the instruction was added and False otherwise.
    def maybe_add_instr(self, instr):
        if instr.id not in self.instructions:
            self.instructions[instr.id] = instr
            return True
        return False

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
    def __init__(self, instruction_json, iid, bb):
        # Instruction ID is useful when we keep record of Instructions in Variables
        self.id = iid         
        # Parent BasicBlock
        self.bb = bb
        # Parent FunctionCFG
        self.f = bb.f 
        # Operation name e.g. alloc, add, br, phi
        self.opname = instruction_json['opname']

        # Variable defined by this instruction
        self.definition = self.f.get_or_create_variable(instruction_json['def'], self)

        # Variables that are used by this instruction. Normally it is a list of Variables
        # except for the PHI instruction when it is a list of pairs (bblock-id, Variable),
        # meaning from which basic block the given variable is coming from.
        # We use basic block id instead of BasicBlock object because we cannot be sure if
        # the BasicBlock has been already created (e.g. in case of loop).
        self.phi_uses = None
        self.uses = None

        if self.is_phi():
            self.phi_uses = []
            for op_json in instruction_json['use']:
                bb_name = op_json['bb']
                bb_id = bb_name.split(SEPARATOR)[0]
                val_name = op_json['val']
                use = (bb_id, self.f.get_or_create_variable(val_name, self))
                self.phi_uses.append(use)
            
        else :
            self.uses = []
            for use in instruction_json['use']:
                v = self.f.get_or_create_variable(use, self)
                self.uses.append(v)

        
        self.live_in = None
        self.live_out = None


    def is_phi(self):
        return self.opname == "phi"

    # Returns pretty string representation of this instruction
    def pretty_str(self, kwargs):
        live_vars = kwargs.get("live_vars", [])
        res = Colors.YELLOW + self.definition.pretty_str(kwargs) + " = " 
        res = res + Colors.RED + self.opname + Colors.YELLOW
        if self.is_phi():
            for use in self.phi_uses:
                bb_id, v = use
                res = res + " (" + bb_id + " -> " + v.pretty_str(kwargs) + "),"
        else:
            for use in self.uses:
                res = res + " " + use.pretty_str(kwargs) + ","
            
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
    def __init__(self, bblock_json, function):
        # The parent function this basic block is located in.
        self.f = function

        # We give each instruction a number (or id). Ids may not correspond with
        # instruction's order in basic block because in the future we may need to
        # add a new instruction in the middle of the block granting it a new, higher
        # number.
        self.instr_counter = 0 

        bbinfo = bblock_json['name'].split(SEPARATOR)
        self.id = bbinfo[0]
        self.llvm_id = None
        if len(bbinfo)>1 and bbinfo[1] != '':
            self.llvm_id = bbinfo[1]

        # BasicBlock consists of a list of instructions.
        self.instructions = [
                self.create_instruction(instr_json) 
                for instr_json in bblock_json['instructions']
                ]

        # dictionaries of predecessors and successors {bblock-id: BasicBlock}
        self.preds = None
        self.succs = None

        self.instr_live_in = None
        self.instr_live_out = None

        self.defs = None
        self.uevs = None

        self.live_in = None
        self.live_out = None

        self.dominators = None

    def create_instruction(self, instr_json):
        i = Instruction(instr_json, self.instr_counter, self)
        self.instr_counter += 1
        return i

    # Computes variable sets (defs, uevs) for this basic block.
    # defs - variables defined in the basic block
    # uevs - variables that are used before any redefinition. Here such set
    #        is computed per each incomming edge separately because of PHI
    #        functions. PHI functions use given variables depending on which
    #        edge was chosen during program execution.
    #
    # It doesn't take into account global variables.
    def compute_defs_and_uevs(self):
        pred_ids = self.preds.keys()
        defs = set() #{pred_id: set() for pred_id in pred_ids}
        uevs = {pred_id: set() for pred_id in pred_ids}
    
        for instr in self.instructions:
            if instr.is_phi():
                for (bb_id, use) in instr.phi_uses:
                    if use not in defs and use.local:
                        uevs[bb_id].add(use)
            else:
                for use in instr.uses:
                    # Each use add to each edge
                    if use not in defs and use.local:
                        for pred_id in pred_ids:
                            uevs[pred_id].add(use)

            defs.add(instr.definition)

        self.defs = defs
        self.uevs = uevs

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
        if self.llvm_id is not None:
            res = res + "("+self.llvm_id+")"

        for instr in self.instructions:
            res = res + "\n  > " + instr.pretty_str(kwargs)
        
        # successors
        res = res + "\n  SUCC: ["
        succs_ids = self.succs.keys()
        for i in range(len(succs_ids)):
            if i:
                res = res + ", "
            res = res + succs_ids[i]
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
            assert self.uevs is not None
            # uevars
            res = res + "\n  UEV: "
            iter_uevs = [(k,v) for (k,v) in self.uevs.iteritems()]
            for i in range(len(iter_uevs)):
                if i:
                    res = res + "\n       "
                (bid, uevset) = iter_uevs[i]
                res = res + "(" + bid + " -> "
                uevlist = list(uevset)
                res = res + "["
                for i in range(len(uevlist)):
                    if i:
                        res = res + ", "
                    res = res + uevlist[i].pretty_str(kwargs)
                res = res + "]"    
                res = res + ")"
            
            # definitions
            assert self.defs is not None
            defs = list(self.defs)
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
        self.vars = {} # dictionary of variables in this function

        # Function consists of basic blocks
        bblocks_json = function_json['bblocks']
        bblocks_list = [BasicBlock(bb_json, self) for bb_json in bblocks_json]
        self.bblocks = {bb.id: bb for bb in bblocks_list}

        # Entry block
        entry_block_id = get_id_from_full_name(function_json['entry_block'])
        self.entry_block = self.bblocks[entry_block_id]

        # Liveness sets
        self.bb_live_in = None
        self.bb_live_out = None
       
        # For each basic block set its predecessors and successors
        for bbj in bblocks_json:
            _id = get_id_from_full_name(bbj['name'])

            pred_ids = [get_id_from_full_name(fname) for fname in bbj['predecessors']]
            preds = {pred_id: self.bblocks[pred_id] for pred_id in pred_ids}

            succ_ids = [get_id_from_full_name(fname) for fname in bbj['successors']]
            succs = {succ_id: self.bblocks[succ_id] for succ_id in succ_ids}

            self.bblocks[_id].preds = preds
            self.bblocks[_id].succs = succs

    # Checks if there exists a variable with the same id. If so, it return this variable,
    # and if not, it creates new variable with this id. In both cases we "maybe-add" the
    # instruction the variable is used by. 
    def get_or_create_variable(self, name, parent_instr):
        vinfo = name.split(SEPARATOR)
        vid = vinfo[0]
        
        if vid in self.vars:
            v = self.vars[vid]
            v.maybe_add_instr(parent_instr)
            return v
        else:
            v = Variable(name, self)
            v.maybe_add_instr(parent_instr)
            self.vars[vid] = v
            return v

    # Assumes there exists a varialbe with given id in the function's dictionary and returns
    # this variable.
    def get_variable(self, vid):
        assert vid in self.vars
        return self.vars[vid]

    # Computes definitions and upword-exposed variables for each basic block.
    def compute_defs_and_uevs(self):
        for bb in self.bblocks.values():
            bb.compute_defs_and_uevs()

    # Performs liveness analysis - for each basic block and instruction computes 
    # live_in and live_out variable sets
    # Returns dictionaries live_in: {bb.id -> set of live-in vars} and live_out accordingly.
    #
    # ordered_bbs (optional) - a list of ids - the order of bblocks in which to perform
    #                          round robin algorithm, e.g. in reverse postorder.
    def perform_liveness_analysis(self, ordered_bbs = None):
        if ordered_bbs is None:
            ordered_bbs = self.bblocks.values()

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
                for succ in bb.succs.values():
                    # To the current basic block's live-out set we add all 
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
            ordered_bbs = self.bblocks.values()

        for bb in ordered_bbs:
            bb.dominators = set({bb})

        change = True
        while change:
            change = False
        
            for bb in ordered_bbs:
                dominators_size = len(bb.dominators)
                preds_dominators = [pred.dominators for pred in bb.preds.values()]
                if len(preds_dominators) > 0:
                    bb.dominators |= set.intersection(*preds_dominators)

                if len(bb.dominators) > dominators_size:
                    change = True

    # Returns pretty string representation of this function
    def pretty_str(self, **kwargs):
        print_bb_live_sets = kwargs.get("bb_live_sets", True)
        print_uev_def = kwargs.get("uev_def", True)

        res = "FUNCTION " + self.name
        for bb in self.bblocks.values():
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
    
