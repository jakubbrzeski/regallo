import utils
import json
from copy import deepcopy

#########################################################################
############################### CFG MODEL ###############################
#########################################################################

# Variable is an allocable value used or defined by Instructions.
# Allocable means it is interesting for register allocation, in contrary to
# such values as constants and labels that are also instructions' operands
# but do not need to reside in registers.
# Variable names are of the form id/llvm_name. The llvm_name may be empty.
class Variable:
    def __init__(self, name):
        vinfo = name.split(utils.SEPARATOR)
        self.id = vinfo[0]

        # Allocation computed by register allocator i.e. mapping
        # from instruction-id where the variable is used or defined
        # to register or memory slot.
        self.alloc = {}
        
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

    def is_spilled_at(self, instr):
        if instr.id not in self.alloc:
            return False
        return utils.is_slotname(self.alloc[instr.id])

class Instruction:
    PHI = "phi"
    LOAD = "load_"
    STORE = "store_"
    MOV = "mov"
    BRANCH = "br"

    def __init__(self, bb, defn, opname, uses, uses_debug=None):
        # Parent BasicBlock.
        self.bb = bb

        # Parent Function.
        self.f = bb.f 

        # Instruction unique id.
        self.id = self.f.get_free_iid()

        # Number of instruction in linearized CFG.
        self.num = None

        # Variable defined by this instruction.
        self.definition = defn

        # Operation name e.g. alloc, add, br, phi.
        self.opname = opname

        # Variables that are used by this instruction. It doesn't include constants, labels
        # or any other values that are not interesting for register allocator. 
        # All values (also constants and labels) are hold in self.uses_debug (see below).
        # If this is PHI instruction, self.uses is turned into dictionary {pred block id: var}.
        # TODO describe set
        self.uses = uses if uses else set()

        # If this is PHI instruction, phi_preds maps variable id to corresponding
        # predecessor block id.
        self.phi_preds = None

        # List of all values (not only allocable Variables) used by the instruction.
        # If this is PHI instruction, self.uses_debug is turned into dictionary {pred block if: value}
        self.uses_debug = uses_debug if uses_debug else []
      
        # Set of variables live-in and live-out at this instruction.
        # and dictionaries of live variables with their allocations
        self.live_in = None
        self.live_out = None
        self.live_in_with_alloc = None
        self.live_out_with_alloc = None

        if opname == Instruction.PHI:
            phi_uses = {}
            self.phi_preds = {}
            for (bid, var) in uses:
                phi_uses[bid] = var
                self.phi_preds[var.id] = bid
            
            self.uses = phi_uses
            phi_uses = {}
            for (bid, val) in uses_debug:
                phi_uses[bid] = val

            self.uses_debug = phi_uses

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id
            
        return False

    # Create a deep copy of the instruction inside Basic Block cbb.
    # Assumes that cbb.f has already all variable regsitered in f.vars.
    def copy(self, cbb):
        cuses = set()
        cuses_debug = []
        cf = cbb.f
        if self.is_phi():
            cuses = [(bid, cf.vars[v.id]) for (bid,v) in self.uses.iteritems()]
            for (bid, val) in self.uses_debug.iteritems():
                if isinstance(val, Variable):
                    cuses_debug.append((bid, cf.vars[val.id]))
                else:
                    cuses_debug.append((bid, val))
            
        else:
            cuses = set([cf.vars[v.id] for v in self.uses])
            for val in self.uses_debug:
                if isinstance(val, Variable):
                    cuses_debug.append(cf.vars[val.id])
                else:
                    cuses_debug.append(val)

      
        cdefn = cf.vars[self.definition.id] if self.definition else None
        ci = Instruction(cbb, cdefn, self.opname, cuses, cuses_debug)

        ci.num = self.num
        ci.live_in_with_alloc = {cf.vars[v.id]: alloc for (v, alloc) in self.live_in_with_alloc.iteritems()}
        ci.live_out_with_alloc = {cf.vars[v.id]: alloc for (v, alloc) in self.live_out_with_alloc.iteritems()}
        
        ci.live_in = set(ci.live_in_with_alloc.keys())
        ci.live_out = set(ci.live_out_with_alloc.keys())
        
        return ci


    # Creates new Instruction object from given json, in the Basic Block bb.
    @classmethod
    def from_json(cls, instruction_json, bb):
        opname = instruction_json['opname']
        defn = bb.f.get_or_create_variable(instruction_json['def'])
        is_phi = (opname == Instruction.PHI)
        uses = set()
        uses_debug = []

        # Setting up uses and phi predecessors.
        for op_json in instruction_json['use']:
            val_name = op_json['val'] if is_phi else op_json
            bb_id = utils.extract_id(op_json['bb']) if is_phi else None

            if utils.is_varname(val_name):
                v = bb.f.get_or_create_variable(val_name)
                if is_phi:
                    uses.add((bb_id, v))
                    uses_debug.append((bb_id, v))
                else:
                    uses.add(v)
                    uses_debug.append(v)

            elif utils.is_bbname(val_name): # label, keep just id string.
                if is_phi:
                    uses_debug.append((bb_id, utils.extract_id(val_name)))
                else:
                    uses_debug.append(utils.extract_id(val_name))
            else:
                if is_phi:
                    uses_debug.append((bb_id, val_name))
                else:
                    uses_debug.append(val_name)

        return cls(bb, defn, opname, uses, uses_debug)

    def is_phi(self):
        return self.opname == Instruction.PHI

    # Returns true if this instruction is a MOV between variables
    # with the same registers assigned.
    def is_redundant(self):
        is_mov = (self.opname == Instruction.MOV)
        if is_mov and self.definition and self.uses:
            alloc1 = self.definition.alloc.get(self.id, None)
            alloc2 = (list(self.uses)[0]).alloc.get(self.id, None)
            if alloc1 and alloc2 and (alloc1 == alloc2):
                return True

        return False


    def get_loop_depth(self):
        assert self.f.loops is not None
        if self.bb.loop is None:
            return 0
        return self.bb.loop.depth

    def register_pressure_in(self):
        return len(self.live_in)

    def register_pressure_out(self):
        return len(self.live_out)

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
        
        # List of phi instructions if there are any in this block.
        self.phis = []

        # Dictionaries of predecessors and successors {bblock-id: BasicBlock}.
        self.preds = {}
        self.succs = {}

        # Sets of
        # - definitions and upward-exposed variables (used before any redefinition)
        # - definitions and upward-exposed registers
        # - dictionary of definitions and upward-exposed variables with their allocations.
        self.defs = set()
        self.uevs = set()
        self.uevs_with_alloc = {}
        self.defs_with_alloc = {}


        # Sets of:
        # - live-in and live-out variables in this block.
        # - dictionary of live variables and their allocations. 
        self.live_in = set()
        self.live_out = set()
        self.live_in_with_alloc = {}
        self.live_out_with_alloc = {}

        # Set of dominators of this basic block.
        self.dominators = set()

        # The smallest Loop (in inclusion order) this block belongs to or None if it's not
        # inside any loop.
        self.loop = None

    # Creates new Basic Block object from given json inside provided Function f.
    @classmethod
    def from_json(cls, bblock_json, f):
        bbinfo = bblock_json['name'].split(utils.SEPARATOR)
        bid = bbinfo[0]
        llvm_name = None

        if len(bbinfo)>1 and bbinfo[1] != '':
            llvm_name = bbinfo[1]

        bb = cls(bid, f, llvm_name)

        for instr_json in bblock_json['instructions']:
            instr = Instruction.from_json(instr_json, bb)
            bb.instructions.append(instr)
            if instr.is_phi():
                bb.phis.append(instr)

        return bb

    # Returns true if all its instructions are redundant.
    # see Instruction.is_redundant(self)
    # Such BasicBlocks may be created after phi_elimination.
    def is_redundant(self):
        for instr in self.instructions:
            if not instr.is_redundant():
                return False

        return True

    def dominates(self, another):
        return self in another.dominators

    def strictly_dominates(self, another):
        return self in another.dominators and self.id != another.id

    def set_instructions(self, new_instructions):
        self.instructions = new_instructions
        self.phis = []
        for instr in new_instructions:
            if instr.is_phi():
                self.phis.append(instr)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id
        return False

    def __hash__(self):
        return int(self.id[2:]) # we omit "bb" - first two characters of id

    def __repr__(self):
        return str(self.id)

    def is_loop_header(self):
        if self.loop is None:
            return False
        
        return self.loop.header.id == self.id

    def first_instr(self):
        return self.instructions[0]

    def last_instr(self):
        return self.instructions[-1]

    def register_pressure_in(self):
        return len(self.live_in)

    def register_pressure_out(self):
        return len(self.live_out)

    # Register pressure at the given point of the program is a number
    # of currently live variables. We define minimal register pressure
    # as the register pressure in the program where all variables were
    # spilled. Then, it should amount to the maximum over a number of 
    # used variables in each instruction.
    def minimal_register_pressure(self):
        max_uses = 0
        for instr in self.instructions:
            if not instr.is_phi():
                max_uses = max(max_uses, len(instr.uses))

        return max_uses

    # Computes: 
    # - sets of defined and upward-exposed variables (defs and uevs)
    # - dictionary of these variables to their allocations (~with_alloc)
    # - sets of defined and upward-exposed registers (reg_defs and reg_uevs)
    def compute_defs_and_uevs(self):
        defs_with_alloc = {}
        uevs_with_alloc = {}
    
        for instr in self.instructions:
            if not instr.is_phi():
                for var in instr.uses:
                    if var not in defs_with_alloc:
                        uevs_with_alloc[var] = var.alloc.get(instr.id, None)
        
            if instr.definition:
                var = instr.definition
                defs_with_alloc[var] = var.alloc.get(instr.id, None)
            
        self.defs_with_alloc = defs_with_alloc
        self.uevs_with_alloc = uevs_with_alloc
        self.defs = set(defs_with_alloc.keys())
        self.uevs = set(uevs_with_alloc.keys())

    # Liveness analysis for instructions.
    #
    # Params:
    # check_correctnes - if True, tests if allocation of variables is correct
    #                    on the basic block level, i.e. whether variable live
    #                    -in and -out at the instruction share the same register.
    def perform_instr_liveness_analysis(self, check_correctness=False):
        current_live_dict = self.live_out_with_alloc.copy()

        def alloc_correct(instr, var):
            instr_alloc = var.alloc.get(instr.id, None)
            dict_alloc = current_live_dict[var]
            if instr_alloc and dict_alloc and (instr_alloc != dict_alloc):
                return False
            return True

        for instr in self.instructions[::-1]:
            instr.live_out_with_alloc = current_live_dict.copy()
            instr.live_out = set(instr.live_out_with_alloc.keys())

            if instr.definition:
                var = instr.definition
                if var in current_live_dict:
                    # CORRECTNESS CHECK
                    if check_correctness and not alloc_correct(instr, var):
                        return False
                    del current_live_dict[var]

            if not instr.is_phi(): # ?
                for var in instr.uses:
                    if var in current_live_dict:
                        # CORRECTNESS CHECK
                        if check_correctness and not alloc_correct(instr, var):
                            return False
                    else:    
                        current_live_dict[var] = var.alloc.get(instr.id, None)

            instr.live_in_with_alloc = current_live_dict.copy()
            instr.live_in = set(instr.live_in_with_alloc.keys())

        return True

# Loop is a list of basic blocks, the first of which is a header and last - a tail.
# Loops may be nested, so it has a parent field which is the 'nearest' parent in the
# dominance order.
class Loop:
    def __init__(self, header, tail, body):
        self.header = header
        self.tail = tail
        self.body = body
        self.parent = None
        self.depth = None
        self.id = (header.id, tail.id)

    def inner_of(self, another):
        return another.header.strictly_dominates(self.header) and self.header.strictly_dominates(another.tail)


class Function:
    def __init__(self, fname):
        self.name = fname

        # Dictionary of all variables in this function {vid: Variable}.
        self.vars = {}
        self.free_vid = "v1"

        # Counter of instruction ids.
        self.instr_counter = 0

        # Dictionary of basic blocks {bid: bb}.
        self.bblocks = {}
        self.free_bid = "bb1"

        # Entry basic block
        self.entry_bblock = None

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

    # Deepcopy of the function.
    def copy(self):
        cf = Function(self.name)
        cf.vars = {vid: deepcopy(var) for (vid, var) in self.vars.iteritems()}
        cf.instr_counter = self.instr_counter

        for (bid, bb) in self.bblocks.iteritems():
            cbb = BasicBlock(bid, cf, bb.llvm_name)
            cf.bblocks[bid] = cbb


        cf.entry_bblock = cf.bblocks[self.entry_bblock.id]

        # Copy basic blocks.
        for (bid, bb) in self.bblocks.iteritems():
            cbb = cf.bblocks[bid] # copy
            
            cbb.preds = {k: cf.bblocks[k] for k in bb.preds.keys()}
            cbb.succs = {k: cf.bblocks[k] for k in bb.succs.keys()}
            cbb.dominators = set([cf.bblocks[dom.id] for dom in bb.dominators])
            
            cbb.uevs = set([cf.get_or_create_variable(v.id) for v in bb.uevs])
            cbb.defs = set([cf.get_or_create_variable(v.id) for v in bb.defs if v is not None])
            
            cbb.live_in_with_alloc = {cf.get_or_create_variable(v.id): alloc for v, alloc in bb.live_in_with_alloc.iteritems()}
            cbb.live_out_with_alloc = {cf.get_or_create_variable(v.id): alloc for v, alloc in bb.live_out_with_alloc.iteritems()}
            
            cbb.live_in = set(cbb.live_in_with_alloc.keys())
            cbb.live_out = set(cbb.live_out_with_alloc.keys())
            
            #instructions:
            for instr in bb.instructions:
                ci = instr.copy(cbb)
                if ci.is_phi():
                    cbb.phis.append(ci)
                cbb.instructions.append(ci)

        # Loops.
        cloopsmap = {}
        for loop in self.loops:
            cheader = cf.bblocks[loop.header.id]
            ctail = cf.bblocks[loop.tail.id]
            cbody = [cf.bblocks[bb.id] for bb in loop.body]
            cloop = Loop(cheader, ctail, cbody)
            cloop.depth = loop.depth
            cloopsmap[cloop.id] = cloop
            cf.loops.append(cloop)

        # Loop parents.
        for loop in self.loops:
            if loop.parent is not None:
                cloopsmap[loop.id].parent = cloopsmap[loop.parent.id]

        return cf 

    # Returns the maximum over minimal register pressure
    # values in all basic blocks in this function.
    # see BasicBlock.minimal_register_pressure()
    def minimal_register_pressure(self):
        max_pressure = 0
        for bb in self.bblocks.values():
            max_pressure = max(max_pressure, bb.minimal_register_pressure())

        return max_pressure

    def set_bblocks(self, bbs_dict, entrybb):
        self.entry_bblock = entrybb
        self.bblocks = bbs_dict
        self.llvm_name2id = {}

        for bb in self.bblocks.values():
            if bb.llvm_name is not None:
                self.llvm_name2id[bb.llvm_name] = bb.id


    # Finds and returns the first available variable id.
    def find_free_vid(self):
        while (self.free_vid in self.vars):
            num = int(self.free_vid[1:])
            self.free_vid = "v" + str(num+1)

        return self.free_vid

    # Finds and returns the first available basic block id.
    def find_free_bid(self):
        while (self.free_bid in self.bblocks):
            num = int(self.free_bid[2:])
            self.free_bid = "bb" + str(num+1)

        return self.free_bid

    # Checks if there exists a variable with the same id. If so, it return this variable,
    # and if not, it creates new variable with this id. In both cases we "maybe-add" the
    # instruction the variable is used by. 
    def get_or_create_variable(self, name=None):
        if name is None:
            free_vid = self.find_free_vid()
            v = Variable(free_vid)
            self.vars[free_vid] = v
            return v

        assert utils.is_varname(name)

        vinfo = name.split(utils.SEPARATOR)
        vid = vinfo[0]
        v = None 

        if vid in self.vars:
            v = self.vars[vid]
        else:
            v = Variable(name)
            self.vars[vid] = v
        
        return v

    def create_new_basic_block(self, bid=None):
        if bid is None:
            bid = self.find_free_bid()
        bb = BasicBlock(bid, self)
        self.bblocks[bid] = bb
        return bb

    # Inserts bti between bb1 and bb2.
    def insert_basic_block_between(self, bti, bb1, bb2):
        # Add edge bb1-bti 
        bti.preds[bb1.id] = bb1
        bb1.succs[bti.id] = bti
        # Add edge bti-bb2
        bti.succs[bb2.id] = bb2
        bb2.preds[bti.id] = bti
        # Delete edge (bb1, bb2).
        del bb2.preds[bb1.id]
        del bb1.succs[bb2.id]

        # For all phi instructions in bb2, replace all 
        # entries (bb1.id -> val) with (bti.id -> val)
        for phi in bb2.phis:
            v = phi.uses_debug[bb1.id]
            del phi.uses_debug[bb1.id]
            phi.uses_debug[bti.id] = v

            if bb1.id in phi.uses: # false if val is const
                del phi.uses[bb1.id]
                phi.uses[bti.id] = v # if condition was true, it is the same var

    def temp_variable(self):
        return self.get_or_create_variable("v0")

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

    # For each basic block and their instructions computes liveness sets:
    # live_in and live_out - sets of live-in and live-out variables
    # live_in_with_alloc and live_out_with_alloc - sets of live variables with their allocations
    #
    # Params:
    # ordered_bbs - optional list of ordered basic blocks the analysis should be performed on.
    # check_correctness - if True, tests whether variables allocation is correct on the function level:
    #                     i.e. whether variables live-in and live-out on any edge between two basic blocks
    #                     have the same register assign.
    def perform_liveness_analysis(self, ordered_bbs = None, check_correctness = False):
        live_in_with_alloc = {}
        live_out_with_alloc = {}

        for bb in self.bblocks.values():
            bb.compute_defs_and_uevs()
            live_in_with_alloc[bb.id] = {}
            live_out_with_alloc[bb.id] = {}

        if ordered_bbs is None:
            ordered_bbs = self.bblocks.values()

        # Checks if all vars contained in both d1 and d2 have the same allocation.
        def alloc_correct(d1, d2):
            for (var, alloc) in d1.iteritems():
                alloc2 = d2.get(var, None)
                if alloc2 and alloc != alloc2:
                    return False

            return True

        change = True
        while change:
            change = False
            for bb in ordered_bbs:
                # LIVE-OUT
                live_out_size = len(live_out_with_alloc[bb.id])
                for succ in bb.succs.values():

                    # CORRECTNESS CHECK
                    if check_correctness and not alloc_correct(live_out_with_alloc[bb.id], live_in_with_alloc[succ.id]):
                        return False

                    live_out_with_alloc[bb.id].update(live_in_with_alloc[succ.id])
                    # We follow the convention that variable used in a phi instruction is not live at this instruction
                    # nor live-in at this basic block BUT is live-out at its predecessor.
                    for phi in succ.phis:
                        if bb.id in phi.uses:
                            var = phi.uses[bb.id]
                            live_out_with_alloc[bb.id][var] = var.alloc.get(phi.id, None)

                # LIVE-IN
                # Variable is live-in at the basic block.
                # - it is upword-exposed in this basic block
                # - OR is live on the exit from this block and not defined in this block.
                live_in_size = len(live_in_with_alloc[bb.id])
                live_out_minus_defs = {var: alloc for (var, alloc) in live_out_with_alloc[bb.id].iteritems() if var not in bb.defs_with_alloc}

                # CORRECTNESS CHECK
                if check_correctness and not alloc_correct(bb.uevs_with_alloc, live_out_minus_defs):
                    return False

                live_in_with_alloc[bb.id] = bb.uevs_with_alloc.copy()
                live_in_with_alloc[bb.id].update(live_out_minus_defs)
                    
                if len(live_in_with_alloc[bb.id]) > live_in_size or len(live_out_with_alloc[bb.id]) > live_out_size:
                    change = True

        for bb in ordered_bbs:
            bb.live_in_with_alloc = live_in_with_alloc[bb.id]
            bb.live_out_with_alloc = live_out_with_alloc[bb.id]
            bb.live_in = set(bb.live_in_with_alloc.keys())
            bb.live_out = set(bb.live_out_with_alloc.keys())

        # LIVENESS ANALYSIS BETWEEN INSTRUCTIONS
        for bb in ordered_bbs:
            correct = bb.perform_instr_liveness_analysis()
            if check_correctness and not correct:
                return False

        return True

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

    def perform_full_analysis(self):
        utils.number_instructions(utils.reverse_postorder(self))
        self.perform_liveness_analysis()
        self.perform_dominance_analysis()
        self.perform_loop_analysis()


    # Sanity check.
    # Checks whether: 
    # - each variable that is used at least once is allocated to register.
    # - allocation is consistent (two subsequent uses with no def bewteen have the same register assigned)
    # - in every program point, each live variable has different register allocated.
    def allocation_is_correct(self):
        result = self.perform_liveness_analysis(check_correctness=True)
        if not result:
            return False

        for bb in self.bblocks.values():
            for instr in bb.instructions:
                # Each live variable must have allocation.
                for (var, alloc) in instr.live_out_with_alloc.iteritems():
                    if alloc is None:
                        return False

                tmp = set()
                for (var, alloc) in instr.live_out_with_alloc.iteritems():
                    # Each live variable must have register assigned.
                    if not utils.is_regname(alloc):
                        return False

                    # Variable must have different register assigned.
                    if alloc in tmp:
                        return False
                    tmp.add(alloc)

        return True


# Module represents a program and consists of list of functions.
class Module:
    def __init__(self, functions):
        self.functions = {f.name: f for f in functions}

    @classmethod
    def from_json(cls, json):
        functions = [Function.from_json(f_json) for f_json in json]
        return cls(functions)

    @classmethod
    def from_file(cls, filename):
        module_json = None
        with open(filename) as f:
            module_json = json.load(f)

        if module_json:
            return cls.from_json(module_json)

        return None

    def perform_full_analysis(self):
        for f in self.functions.values():
            f.perform_full_analysis()

    def copy(self):
        copies = [f.copy() for f in self.functions.values()]
        return Module(copies)

