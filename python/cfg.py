SEPARATOR = "/" # Should be the same as in cfgextractor in C++

def get_id_from_full_name(full_name):
    _id, _, _ = full_name.split(SEPARATOR)
    return _id

#########################################################################
############################### CFG MODEL ###############################
#########################################################################

# Variable names are of the form id/llvm_id/{L,G}. The llvm_id may be empty.
class Variable:
    def __init__(self, name, function):
        # The Function we operate in
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


class Instruction:
    def __init__(self, instruction_json, iid, bb):
        # Instruction ID is useful when we keep record of Instructions in Variables
        self.id = iid         
        # Parent BasicBlock
        self.bb = bb
        # Parent Function
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

        # Dictionaries of predecessors and successors {bblock-id: BasicBlock}.
        self.preds = None
        self.succs = None

        # The uevs set is a dictionary of sets of upword-exposed variables (variables that
        # are used before any redefinition in this block) computed per incoming edge,
        # i.e uevs = {predecessor_id: set of variables}. It is because of PHI functions,
        # where the given variable is used depending on where the control flow comes from.
        self.uevs = None
        self.defs = None

        # The live_in sets are computed per incoming edge because of PHI functions:
        # so live_in = {predecessor_id: set of live variablie}.
        # live_out set is a sum of live_in variables from all successors.
        self.live_in = None
        self.live_out = None

        # Set of dominators of this basic block.
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

    # For each instruction computes sets of live-in and
    # live-out variables (before and after the instruction)
    def perform_instr_liveness_analysis(self):
        current_live_set = set()
        for pred_id in self.preds.keys():
            current_live_set |= self.live_in[pred_id].copy()
            
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


class Function:
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

        # initialize sets
        for bb in ordered_bbs:
            assert bb.defs is not None and bb.uevs is not None
            bb.live_in = {pred_id: set() for pred_id in bb.preds.keys()}
            bb.live_out = set()

        change = True
        iterations = 0
        while change:
            iterations += 1
            change = False
            for bb in ordered_bbs:
                live_out_size = len(bb.live_out)
                for succ in bb.succs.values():
                    # To the current basic block's live-out set we add all 
                    # variables that are live on the edge to this successor.
                    bb.live_out |= succ.live_in[bb.id]
                
                if len(bb.live_out) > live_out_size:
                    change = True
                # Live-in set of the basic block consists of all variables
                # that are upword-exposed or live-out but not defined in this block.
                for pred_id in bb.preds.keys():
                    live_in_size = len(bb.live_in[pred_id])
                    # Main part of the algorithm - updating live-in set.
                    # Variable is in live on the edge between blocks (p --> bb)
                    # if it is upword-exposed in bb (i.e. used before any redefinition)
                    # or is live on the exit from bb and not defined in this block.
                    bb.live_in[pred_id] = (bb.uevs[pred_id] | (bb.live_out - bb.defs))
                    if len(bb.live_in[pred_id]) > live_in_size:
                        change = True

        for bb in ordered_bbs:
            bb.perform_instr_liveness_analysis() # updates liveness for each instr

        print "Liveness analysis done, #iterations = ", iterations

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
    
