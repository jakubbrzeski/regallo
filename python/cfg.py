import utils

#########################################################################
############################### CFG MODEL ###############################
#########################################################################

# Variable is an allocable value used or defined by Instructions.
# Allocable means it is interesting for register allocation, in contrary to
# such values as constants and labels that are also instructions' operands
# but do not need to reside in registers.
# Variable names are of the form id/llvm_name. The llvm_name may be empty.
class Variable:
    def __init__(self, name, f):
        # The Function we operate in.
        self.f = f
       
        # Dictionary of instructions the variable is defined in. It may be empty for some
        # variables that are defined outside the function body (e.g. its
        # arguments). We rather operate on SSA form so the variable should have
        # only one definition but we keep dictionary for possible experiments.
        # {iid: Instruction}
        self.defs = {}

        # Dictionary of instructions the variable is used in.
        # {iid: Instruction}
        self.uses = {}

        vinfo = name.split(utils.SEPARATOR)
        self.id = vinfo[0]
        
        self.llvm_name = None
        if len(vinfo) > 1 and vinfo[1] != '':
            self.llvm_name = vinfo[1]

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

    # Adds the given Instruction to this Variable's record if it's not already there.
    # Returns True if the instruction was added and False otherwise.
    def maybe_add_use(self, instr):
        if instr.id not in self.uses:
            self.uses[instr.id] = instr
            return True
        return False

class Instruction:
    PHI = "phi"
    LOAD = "load"
    STORE = "store"
    MOVE = "move"

    def __init__(self, iid, bb, defn, opname, uses, phi_preds=None, uses_debug=[]):
        # Instruction id.
        self.id = iid

        # Parent BasicBlock.
        self.bb = bb

        # Parent Function.
        self.f = bb.f 

        # Number of instruction. It's something different than id. Id is unique,
        # but we can number the instruction multiple times. It is useful especially
        # when dealing with linearized program , e.g. in linear scan register allocation. 
        #TODO: finish description
        self.num = None

        # Variable defined by this instruction.
        self.definition = defn
        # By the way we update the variable's defs dictionary.
        defn.defs[iid] = self

        # Operation name e.g. alloc, add, br, phi.
        self.opname = opname

        # Variables that are used by this instruction. It doesn't include constants, labels
        # or any other values that are not interesting for register allocator. All values
        # are hold in self.uses_debug (see below).
        # If this is PHI instruction, we keep ids of this basic block predecessors 
        # which correspond to the particular variables in self.uses. It means that
        # self.phi_preds[i] is id of bb where the variable self.uses[i] comes from.
        self.phi_preds = phi_preds
        self.uses = uses

        # Dicitonary {variable id: register}
        self.alloc = {}

        # For each variable we update instructions it is used in.
        for var in uses:
            var.uses[iid] = self

        # Lists of all values (not only allocable Variables) used by the instruction in
        # string format. These are e.g. labels (basic block ids) or constants and are useful
        # for debugging purposes.
        self.uses_debug = uses_debug
      
        # Set of variables live-in and live-out of this instruction.
        self.live_in = None
        self.live_out = None

    @classmethod
    def from_json(cls, instruction_json, bb):
        iid = bb.f.get_free_iid()
        opname = instruction_json['opname']
        defn = bb.f.get_or_create_variable(instruction_json['def'])
        is_phi = (opname == Instruction.PHI)
        phi_preds = None
        uses = []
        uses_debug = []

        # TODO: what if there are two phi_preds but one use variable?
        #       is it possible?
        #       e.g. 
        if is_phi:
            phi_preds = []

        # Setting up uses and phi predecessors.
        for op_json in instruction_json['use']:
            val_name = op_json
            if is_phi:
                val_name = op_json['val']
                bb_id = utils.extract_id(op_json['bb'])
                phi_preds.append(bb_id)

            if utils.is_varname(val_name):
                v = bb.f.get_or_create_variable(val_name)
                uses.append(v)
                uses_debug.append(utils.extract_id(val_name))
            elif utils.is_bbname(val_name): # label, keep just id string.
                uses_debug.append(utils.extract_id(val_name))
            else:
                uses_debug.append(val_name)

        return cls(iid, bb, defn, opname, uses, phi_preds, uses_debug)

    def is_phi(self):
        return self.opname == Instruction.PHI

    def get_loop_depth(self):
        assert self.f.loops is not None
        if self.bb.loop is None:
            return 0
        return self.bb.loop.depth


class BasicBlock:
    def __init__(self, bid, f, llvm_name = None):
        # Id of the basic block of the form "bb[0-9]+".
        self.id = bid

        # Optional name taken from llvm IR.
        self.llvm_name = llvm_name

        # The parent function this basic block is located in.
        self.f = f

        # BasicBlock consists of a list of instructions. 
        self.instructions = []

        # Dictionaries of predecessors and successors {bblock-id: BasicBlock}.
        self.preds = {}
        self.succs = {}

        # The uevs set is a dictionary of sets of upword-exposed variables (variables that
        # are used before any redefinition in this block) computed per incoming edge,
        # i.e uevs = {predecessor_id: set of variables}. It is because of PHI functions,
        # where the given variable is used depending on where the control flow comes from.
        self.uevs = {}
        self.defs = set()

        # The live_in sets are computed per incoming edge because of PHI functions:
        # so live_in = {predecessor_id: set of live variables}.
        # live_out set is a sum of live_in variables from all successors.
        self.live_in_edge = {}
        self.live_in = set()
        self.live_out = set()

        # Set of dominators of this basic block.
        self.dominators = set()

        # The smallest loop (in inclusion order) this bb belongs to or None if it's not
        # inside any loop.
        self.loop = None

    @classmethod
    def from_json(cls, bblock_json, f):
        bbinfo = bblock_json['name'].split(utils.SEPARATOR)
        bid = bbinfo[0]
        llvm_name = None

        if len(bbinfo)>1 and bbinfo[1] != '':
            llvm_name = bbinfo[1]

        bb = cls(bid, f, llvm_name)

        instructions = [
                Instruction.from_json(instr_json, bb)
                for instr_json in bblock_json['instructions']
                ]

        bb.set_instructions(instructions)

        return bb

    def set_instructions(self, new_instructions):
        self.instructions = new_instructions

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id
        return False

    def __hash__(self):
        return int(self.id[2:]) # we omit "b" - first two characters of id

    def __repr__(self):
        return str(self.id)

    def is_loop_header(self):
        if self.loop is None:
            return False
        
        return self.loop.header.id == self.id


    # Computes variable sets (defs, uevs) for this basic block.
    # defs - variables defined in the basic block
    # uevs - variables that are used before any redefinition. We compute
    #        this set per each incoming edge (i.e. per each predecessor block),
    #        because of PHI functions, where it depends on flow direction which
    #        of the variables is going to be used.
    def compute_defs_and_uevs(self):
        pred_ids = self.preds.keys()
        defs = set() #{pred_id: set() for pred_id in pred_ids}
        uevs = {pred_id: set() for pred_id in pred_ids}
    
        for instr in self.instructions:
            if instr.is_phi():
                for (bb_id, use) in zip(instr.phi_preds, instr.uses):
                    if use not in defs:
                        uevs[bb_id].add(use)
            else:
                for use in instr.uses:
                    # Each use add to each edge
                    if use not in defs:
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
            current_live_set |= self.live_in_edge[pred_id].copy()
            
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

# Loop is a list of basic blocks, the first of which is a header and last - a tail.
# Loops may be nested, so it has parent field which is the 'nearest' parent in the
# dominance order.
class Loop:
    def __init__(self, header, tail, body):
        self.header = header
        self.tail = tail
        self.body = body
        self.parent = None
        self.depth = None

    def inner_of(self, another):
        return another.header in self.header.dominators and self.header in another.tail.dominators


class Function:
    def __init__(self, fname):
        self.name = fname

        # Dictionary of all variables in this function {id: Variable}.
        self.vars = {}

        # Counter of instruction ids.
        self.instr_counter = 0

        # Dictionary of basic blocks {bid: bb}.
        self.bblocks = {}

        # Entry basic block
        self.entry_bblock = None

        # Dictionary mapping llvm names of basic blocks to their ids. 
        self.llvm_name2id = {}

        # List of loops in this function
        self.loops = []


    @classmethod
    def from_json(cls, function_json):
        name = function_json['name']
        f = cls(name)

        bblocks_json = function_json['bblocks']
        bblocks_list = [BasicBlock.from_json(bb_json, f) for bb_json in bblocks_json]
        bblocks = {bb.id: bb for bb in bblocks_list}
        
        entry_block_id = utils.extract_id(function_json['entry_block'])
        entry_bblock = bblocks[entry_block_id]

        # For each basic block we set its predecessors and successors.
        for bbj in bblocks_json:
            bid = utils.extract_id(bbj['name'])

            pred_ids = [utils.extract_id(fname) for fname in bbj['predecessors']]
            for pid in pred_ids:
                bblocks[bid].preds[pid] = bblocks[pid]
                bblocks[pid].succs[bid] = bblocks[bid]


        f.set_bblocks(bblocks, entry_bblock)
        return f

    def set_bblocks(self, bbs_dict, entrybb):
        self.entry_bblock = entrybb
        self.bblocks = bbs_dict
        self.llvm_name2id = {}

        for bb in self.bblocks.values():
            if bb.llvm_name is not None:
                self.llvm_name2id[bb.llvm_name] = bb.id

    # Checks if there exists a variable with the same id. If so, it return this variable,
    # and if not, it creates new variable with this id. In both cases we "maybe-add" the
    # instruction the variable is used by. 
    def get_or_create_variable(self, name=None):
        if name is None:
            free_num = len(self.vars) + 1
            vid = "v"+str(free_num)
            v = Variable(vid, self)
            self.vars[vid] = v
            return v

        assert utils.is_varname(name)

        vinfo = name.split(utils.SEPARATOR)
        vid = vinfo[0]
        v = None 

        if vid in self.vars:
            v = self.vars[vid]
        else:
            v = Variable(name, self)
            self.vars[vid] = v
        
        return v

    # Assumes there exists a varialbe with given id in the function's dictionary and returns
    # this variable.
    def get_variable(self, vid):
        assert vid in self.vars
        return self.vars[vid]

    # Returns new Instruction with id assigned.
    def get_free_iid(self):
        iid = self.instr_counter
        self.instr_counter += 1
        return iid

    # Computes definitions and upword-exposed variables for each basic block.
    def compute_defs_and_uevs(self):
        for bb in self.bblocks.values():
            bb.compute_defs_and_uevs()

    # Performs liveness analysis - for each basic block and instruction computes 
    # live_in and live_out variable sets
    #
    # ordered_bbs (optional) - a list of ids - the order of bblocks in which to perform
    #                          round robin algorithm, e.g. in reverse postorder.
    def perform_liveness_analysis(self, ordered_bbs = None):
        if ordered_bbs is None:
            ordered_bbs = self.bblocks.values()

        # initialize sets
        for bb in ordered_bbs:
            assert bb.defs is not None and bb.uevs is not None
            bb.live_in_edge = {pred_id: set() for pred_id in bb.preds.keys()}
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
                    bb.live_out |= succ.live_in_edge[bb.id]
                
                if len(bb.live_out) > live_out_size:
                    change = True

                # Live-in set of the basic block consists of all variables
                # that are upword-exposed or live-out but not defined in this block.
                for pred_id in bb.preds.keys():
                    live_in_size = len(bb.live_in_edge[pred_id])
                    # Main part of the algorithm - updating live-in set.
                    # Variable is in live on the edge between blocks (p --> bb)
                    # if it is upword-exposed in bb (i.e. used before any redefinition)
                    # or is live on the exit from bb and not defined in this block.
                    bb.live_in_edge[pred_id] = (bb.uevs[pred_id] | (bb.live_out - bb.defs))
                    if len(bb.live_in_edge[pred_id]) > live_in_size:
                        change = True

        for bb in ordered_bbs:
            bb.perform_instr_liveness_analysis() # updates liveness for each instr

        for bb in ordered_bbs:
            bb.live_in = set()
            for l in bb.live_in_edge.values():
                bb.live_in |= l


        print "Liveness analysis done, #iterations = ", iterations

    # Performs dominance analysis by updating bb.dominators for each
    # basic block in this function. The bb.dominators is set of basic blocks
    # that dominates bb. 
    # ordered_bbs = ids of basic blocks in order to be processed.
    def perform_dominance_analysis(self, ordered_bbs = None):
        if ordered_bbs is None:
            ordered_bbs = self.bblocks.values()
        else:
            ordered_bbs = [self.bblocks[bid] for bid in ordered_bbs]

        # initialize dom(n) = {all BasicBlcoks}
        for bb in ordered_bbs:
            bb.dominators = set(self.bblocks.values())

        # dom(entry) = {entry}
        self.entry_bblock.dominators = set({self.entry_bblock})

        change = True
        while change:
            change = False
        
            for bb in ordered_bbs:
                dominators_size = len(bb.dominators)
                preds_dominators = [pred.dominators for pred in bb.preds.values()]
               
                bb.dominators = set({bb})
                if len(preds_dominators) > 0:
                    bb.dominators |= set.intersection(*preds_dominators)

                if len(bb.dominators) != dominators_size:
                    change = True

    # Finds all Loops in this function.
    def perform_loop_analysis(self):
        loops = []
        def find_loop((bb_end, bb_start)):
            if bb_start in bb_end.dominators:
                body = []
                def vpre(bb):
                    body.append(bb)
                utils.dfs(bb_end, visited=set(), backwards=True, vpre=vpre, vstop=bb_start)
                loops.append(Loop(bb_start, bb_end, body[::-1])) 

        utils.dfs(self.entry_bblock, visited=set(), ef=find_loop)
        
        # Loop nesting forest
        # Compute parent relation
        # O(|LOOPS|^2)
        for i in range(len(loops)):
            for j in range(len(loops)):
                if i != j:
                    # if i is inside j and j is inside parent[i] (if parent[i] is not None)
                    # then set j as parent of i
                    if loops[i].inner_of(loops[j]) and (loops[i].parent is None 
                            or loops[j].inner_of(loops[i].parent)):
                        loops[i].parent = loops[j]

        # Compute nesting level
        def find_depth(loop):
            if loop.parent is None:
                loop.depth = 1
                return 1
            loop.depth = find_depth(loop.parent) + 1
            return loop.depth

        for loop in loops:
            if loop.depth is None:
                find_depth(loop)

        # For each basic block in any loop, set it's most direct loop it belongs to.
        # O(|BB|^2)
        for loop in loops:
            for bb in loop.body:
                if bb.loop is None:
                    bb.loop = loop
                elif bb.loop.depth < loop.depth:
                    bb.loop = loop

        self.loops = loops

            
class Module:
    def __init__(self, cfg_json):
        self.functions = [Function(f) for f in cfg_json]

