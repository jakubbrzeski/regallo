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

        # Register, memory slot or None if nothing allocated.
        self.alloc = None
        
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

    def is_spilled(self):
        return utils.is_slotname(self.alloc)

class Instruction:
    PHI = "phi"
    LOAD = "load_"
    STORE = "store_"
    MOV = "mov"
    BRANCH = "br"

    def __init__(self, bb, defn, opname, uses, uses_debug, ssa=True):
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

        # False if the instruction was created during phi elimination phase.
        # Otherwise True.
        self.ssa = ssa

        # The first, original instruction this one was copied from (if this is a copy of another
        # copy, we take the another copy's original recursively and so on).
        # Register allocation returns a modified copy of the input function. During sanity check
        # we want to know what was the original instructions of the modified ones.
        self.original = None

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
        ci.original = self.original if self.f.is_copy else self

        ci.num = self.num
        
        ci.live_in = self.live_in
        ci.live_out = self.live_out
        
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
            alloc1 = self.definition.alloc
            alloc2 = (list(self.uses)[0]).alloc
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

        # Sets of definition and upward-exposed variables (used before any redefinition)
        self.defs = set()
        self.uevs = set()


        # Sets of live-in and live-out variables in this basic block.
        self.live_in = set()
        self.live_out = set()

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

    # Maximal register pressure is the maximum over register pressure 
    # values in every point in this basic block.
    def maximal_register_pressure(self):
        max_pressure = self.register_pressure_in()
        for instr in self.instructions:
            max_pressure = max(max_pressure, instr.register_pressure_out())

        return max_pressure

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
    def __init__(self, fname, is_copy=False):
        self.name = fname
        self.is_copy = is_copy

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
        cf = Function(self.name, is_copy=True)
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
            cbb.defs = set([cf.get_or_create_variable(v.id) for v in bb.defs])
            
            cbb.live_in = set([cf.get_or_create_variable(v.id) for v in bb.live_in]) 
            cbb.live_out = set([cf.get_or_create_variable(v.id) for v in bb.live_out])
            
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

    # Returns the maximal "maximal register pressure" over
    # all basic blocks. See BasicBlock.maximal_register_pressure().
    # Any register allocation algorithm should
    # be able to allocate as many registers as the value of maximal
    # register pressure without spilling.
    def maximal_register_pressure(self):
        max_pressure = 0
        for bb in self.bblocks.values():
            max_pressure = max(max_pressure, bb.maximal_register_pressure())

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

    def copy(self):
        copies = [f.copy() for f in self.functions.values()]
        return Module(copies)

