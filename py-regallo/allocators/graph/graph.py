import utils
import spillers
from allocators.allocator import Allocator
from cfg.printer import FunctionString, BBString, Opts

# Build Interference Graph from provided function.
def build_interference_graph(f):
    neighs = {var: set() for var in f.vars.values()}

    for bb in f.bblocks.values():
        live_in = list(bb.live_in)
        # Add clique from all variables live-in at the basic block.
        for v1 in bb.live_in:
            if not v1.is_spilled():
                for v2 in bb.live_in:
                    if v2 not in neighs[v1] and v2 != v1 and not v2.is_spilled():
                        neighs[v2].add(v1)
                        neighs[v1].add(v2)
       
        # For each live-out definition add edges with all other live-out variables.
        for instr in bb.instructions:
            defn = instr.definition
            if defn in instr.live_out and not defn.is_spilled():
                for var in instr.live_out:
                    if defn not in neighs[var]:
                        if var != defn and not var.is_spilled():
                            neighs[var].add(defn)
                            neighs[defn].add(var)


    return neighs

# Assign registers to non-spilled variables in the provided function,
# having 'regcount' available registers. It works under assumption
# that the Interference Graph of the function is 'regcount'-colorable.
def color(f, regcount):
    regset = utils.RegisterSet(regcount)
    for var in f.entry_bblock.live_in:
        var.alloc = regset.get_free()

    def colorbb(bb):
        #print bb.id
        regset.reset()
        for var in bb.live_in:
            if var.alloc and not var.is_spilled():
                # Note carefully that variables defined by phi instructions are
                # live-in at this basic block, although at the moment of coloring
                # their definitions are later so their alloc is None.
                #print "occupy", var, var.alloc
                regset.occupy(var.alloc)


        for instr in bb.instructions:
            #print " ", instr.num, regset.free
            if not instr.is_phi():
                for var in instr.uses:
                    if var not in instr.live_out:
                        #print " ", "setting free", var.alloc, "from", var
                        regset.set_free(var.alloc)

            defn = instr.definition
            if defn and defn.alloc is None and defn in instr.live_out:
                # defn.alloc may not be None if it is spilled or is a variable defined by
                # phi instruction in a loop header which has been assigned a register
                # in the first loop of the function colorbb.
                reg = regset.get_free()
                defn.alloc = reg
                #print " ", "definition", defn, "->", reg

    for bb in utils.reverse_postorder(f):
        colorbb(bb)


# General abstract class for graph coloring register allocation algorithms
class GraphColoringAllocator(Allocator):

    def allocate_registers(self, f, regcount, spilling=True):
        raise NotImplementedError()

    # This function should deal with any function modification needed
    # after single phase of register allocation. E.g. SSA form reconstruction
    # needed if we split life ranges.
    def resolve(self, f):
        raise NotImplementedError()

    def perform_register_allocation(self, f, regcount, spilling=True):
        success = self.allocate_registers(f, regcount, spilling)
        if success:
            self.resolve(f)
            return True

        return False


class BasicGraphColoringAllocator(GraphColoringAllocator):
    def __init__(self, spiller = spillers.default(), name = "Basic Graph Coloring Allocator"):
        self.name = name
        self.spiller = spiller

    def allocate_registers(self, f, regcount, spilling=True):
        max_pressure = f.maximal_register_pressure()
        if max_pressure > regcount:
            if spilling:
                self.spiller.spill_variables(f, regcount)
        
            return False

        color(f, regcount)
        return True

    # Basic GCA doesn't need resolving.
    def resolve(self, f):
        pass
