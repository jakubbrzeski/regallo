import utils
import cfg

# A helper class storing a value plus its allocation (register
# or memory slot in case of Variable, and None in case of const).
class Alloc:
    def __init__(self, val, alloc):
        self.val = val
        self.alloc = alloc

    def allocable(self):
        return utils.is_regname(self.alloc) or utils.is_slotname(self.alloc)

# Takes a list of moves (represented as pairs of Allocs (def,use)) and
# orders it in the way to preserve current register allocation.
# Returns ordered list of moves and list of cycles that need special treatment.
# Based on: 
# S. Hack "Register Allocation for Programs in SSA Form",
# 4.4. Implementing Phi-Operations. 
#
# Contrary to the algorithm, the function returns also self-loops for
# technical reasons - it would break liveness analysis. However, we can 
# later print the function after phi elimination without redundant moves.
def order_moves(moves):
    # All moves that include non-allocable uses such as consts
    # may be safely added to the end.
    non_allocable = [(d,u) for (d,u) in moves if not u.allocable()]
    moves = [(d,u) for (d,u) in moves if u.allocable()]

    # Ordered moves.
    results = [] 
    # List of cycles. We treat cycles separately.
    cycles = [] 
    # Self-loops
    self_loops = []

    # Building graph.
    class Edge:
        def __init__(self, d, u):
            self.d = d
            self.u = u

    # Dictionaries: alloc (reg or memslot) -> incoming or outgoing edges.
    IN = {}
    OUT = {}

    # Initialize.
    for (d,u) in moves:
        IN[d.alloc] = set()
        IN[u.alloc] = set()
        OUT[d.alloc] = set()
        OUT[u.alloc] = set()

    for (d,u) in moves:
        e = Edge(d,u)
        if d.alloc != u.alloc: 
            # We skip self loops here.
            IN[d.alloc].add(e)
            OUT[u.alloc].add(e)
        else:
            self_loops.append((e.d, e.u))
            

    # Find edges (a,b): outdeg(b) == 0.
    leaves = []
    for alloc, edges in OUT.iteritems():
        for edge in edges:
            if not OUT[edge.d.alloc]:
                leaves.append(edge)

    # Iteratively cut edges (a,b): outdeg(b) == 0.
    while leaves:
        edge = leaves.pop()
        results.append((edge.d, edge.u))
        OUT[edge.u.alloc].remove(edge)
        IN[edge.d.alloc].remove(edge)
        
        for rem in OUT[edge.u.alloc]:
            rem.u = edge.d
            OUT[edge.d.alloc].append(rem)

        OUT[edge.u.alloc] = set()
        leaves.extend(IN[edge.u.alloc])

    # Now the graph is either empty or contains only cycles.
    for alloc, edges in IN.iteritems():
        if edges:
            e = edges.pop()
            l = [e]
            while e.u.alloc != alloc:
                e = IN[e.u.alloc].pop()
                l.append(e)
            
            # There are a few possibilities here:
            # - if there is a free register, we can create a new variable 
            #   to store temporarily l[0].u.
            # - if there is no free register we can either:
            #       - represent permutation as a sequense of swap operations
            #         which is rather painful.
            #       - store l[0].u in memory and load at the end of the cycle.
            #
            # We mark this as None and leave the decision to the caller.
            cycle = []
            cycle.append((None, l[0].u))
            cycle.extend([(e.d, e.u) for e in l[1:]])
            cycle.append((l[0].d, None))
            cycles.append(cycle)

    return (self_loops + results + non_allocable, cycles)

# Takes ordered moves as a list of pairs (Alloc(def), Alloc(use))
# and insert them at the end of the given BasicBlock.
def insert_moves(bb, moves):
    for (d,u) in moves:
        if utils.is_regname(d.alloc) and u.alloc is None:
            # d is in register, u.val is const or another non-allocable value.
            instr = cfg.Instruction(bb, d.val, cfg.Instruction.MOV, [], [u.val])
            bb.instructions.append(instr)
            d.val.alloc[instr.id] = d.alloc

        elif utils.is_regname(d.alloc) and utils.is_regname(u.alloc):
            # Both d and u are in registers => produce "d = u"
            instr = cfg.Instruction(bb, d.val, cfg.Instruction.MOV, [u.val], [u.val])
            bb.instructions.append(instr)
            d.val.alloc[instr.id] = d.alloc
            u.val.alloc[instr.id] = u.alloc

        else:
            # After register allocation No variable in phi instructions should be in memory slot.
            assert False

def insert_cycles(bb, cycles):
    endpoints = []
    for cycle in cycles:
        instructions = []
        tmp = bb.f.get_or_create_variable()
        i1, i2 = None, None # endpoints of the cycle
        for (d,u) in cycle:
            instr = None

            if d is None:
                instr = cfg.Instruction(bb, tmp, cfg.Instruction.MOV, [u.val], [u.val])
                u.val.alloc[instr.id] = u.alloc
                i1 = instr
            elif u is None:
                instr = cfg.Instruction(bb, d.val, cfg.Instruction.MOV, [tmp], [tmp])
                d.val.alloc[instr.id] = d.alloc
                i2 = instr
            else:
                instr = cfg.Instruction(bb, d.val, cfg.Instruction.MOV, [u.val], [u.val])
                d.val.alloc[instr.id] = d.alloc
                u.val.alloc[instr.id] = u.alloc

            instructions.append(instr)

        bb.instructions.extend(instructions)
        endpoints.append((i1, i2))

    return endpoints

# If during phi elimination a cycle of movs appears - it
# is cut by storing one of its variables in a new temporary variable.
# This function takes two instructions being the endpoints of a list of
# mov instructions that was created from the cut cycle and checks whether
# this temporary variable can be assigned a register or must be replaced
# by STORE and LOAD operations.
#
# regcount - overall number of registers available. If 0, we replace temp. var by STORE and LOAD.
def allocate_cycle(i1, i2, regcount=0):
    # We want to find a free register between i1 and i2
    # knowing that [i1, i2] is connected interval.
    # Occupied registers are those from i1.reg_live_out + i2.reg_live_in.
   
    if regcount:
        regset = utils.RegisterSet(regcount)
        occupied = i1.reg_live_out | i2.reg_live_in
        free = regset.free - occupied
        reg = free.pop()
        if reg:
            i1.definition.alloc[i1.id] = reg

            list(i2.uses)[0].alloc[i2.id] = reg
            return

    # There is no free register, we need to spill.
    # We change MOVs to STORE and LOAD and use memslot for
    # the temporary variable.

    tmp = i1.definition
    slot = utils.slot(tmp)
   
    # tmp = mov v2 -> store mem(tmp), v2
    i1.opname = cfg.Instruction.STORE
    i1.definition = None
    i1.uses_debug = [slot, list(i1.uses)[0]]
    # i1.uses stay the same.

    # v1 = mov tmp -> v1 = load mem(tmp)
    i2.opname = cfg.Instruction.LOAD
    i2.uses = set()
    i2.uses_debug = [slot]
    # i2.definition stays the same


# Translates the function out of SSA form by deleting phi instructions
# and inserting properly ordered mov instructions in the predecessor blocks.
#
# regcount - overall number of available registers: phi elimination may 
#            need additional register when some moves form a cycle. 
#            If regcount is 0 we spill one value in the cycle to the memory.
#            For details see insert_moves function.
def eliminate_phi(f, regcount=0):

    # Moves between registers may create cycles which need special
    # treatment - we need to remember one variable on the cycle and
    # cut it at that point. If there is a free register, it may
    # reside in a temporary variable. If not, we need to store it in
    # memory. 
    
    # The strategy here is as follows:
    # For each cycle we create a new Variable that stores one value in
    # the cycle. After all cycles are processed, we perform again full
    # liveness analysis for our function (together with register liveness
    # analysis) to obtain register pressure in all points of the program.
    # Then we check if at all cycle endpoints is a free register available.
    # If yes, we allocate it to the corresponding temporary variable we created.
    # If not, we remove the variable and insert store and load respectively
    # at the beginning and the end of the cycle.
    cycles_endpoints = []

    for bb in f.bblocks.values():
        # Process only these bblocks that have any phi instructions.
        if not bb.phis:
            continue

        for pred in bb.preds.values():
            moves = []
            for phi in bb.phis:
                # We represent a move as a pair of Allocs objects, which
                # store the value (Variable or const) and corresponding 
                # allocation (register or memory slot or None).
                d = Alloc(phi.definition, phi.definition.alloc[phi.id])
                u = None
                if pred.id in phi.uses:
                    u = Alloc(phi.uses[pred.id], phi.uses[pred.id].alloc[phi.id])
                else:
                    u = Alloc(phi.uses_debug[pred.id], None)
                moves.append((d,u))
            
            moves, cycles = order_moves(moves)
          
            if moves or cycles:
                # It may happen that moves or cycles are empty,
                # e.g. if there were self loops only.
                # If predecessor has more than one successor, we have to add
                # a new basic block on the edge from pred to bb.
                bti = pred
                if len(pred.succs) > 1:
                    bti = f.create_new_basic_block_between(pred, bb)
                
                if moves:
                    insert_moves(bti, moves)

                if cycles:
                    endpoints = insert_cycles(bti, cycles)
                    cycles_endpoints.extend(endpoints)
            
        # Remove phi instructions from this block.
        bb.instructions = [instr for instr in bb.instructions if not instr.is_phi()]
        bb.phis = []

    f.perform_liveness_analysis()
    f.perform_reg_liveness_analysis()

    for (i1, i2) in cycles_endpoints:
        allocate_cycle(i1, i2, regcount)


# For a function processed by register allocator,
# checks which of its variables have to be spilled into memory and 
# inserts STORE and LOAD operations at proper points of the program.
def insert_spill_code(f):
    # Dictionary of new instructions that will be inserted before
    # of after some current instructions. We don't insert them
    # immediately to avoid linear complexity of list insertion.
    insert_before = {iid: [] for iid in range(f.instr_counter)}
    insert_after  = {iid: [] for iid in range(f.instr_counter)}

    for bb in f.bblocks.values():
        for instr in bb.instructions:
            if instr.definition and instr.definition.is_spilled_at(instr):
                # Insert store after instr.
                # [v1 = ...] -> [v2 = ... ; store mem(v1), v2]  
                v = f.get_or_create_variable()
                memslot = instr.definition.alloc[instr.id]
                instr.definition = v
                
                store = cfg.Instruction(
                        bb = instr.bb, 
                        defn = None, 
                        opname = cfg.Instruction.STORE,
                        uses = set([v]), 
                        uses_debug = [memslot, v])

                insert_after[instr.id].append(store)

            if instr.is_phi():
                for (bid, var) in instr.uses.iteritems():
                    if var.is_spilled_at(instr):
                        # Insert load at the end of predecessor block.
                        # bb:[... = v1] -> pred:[v2 = load mem(v1)] bb:[ ... = v2]
                        pred = f.bblocks[bid]
                        v = f.get_or_create_variable()
                        memslot = var.alloc[instr.id]
                        instr.uses[bid] = v
                        instr.uses_debug[bid] = v

                        load = cfg.Instruction(
                                bb = pred,
                                defn = v,
                                opname = cfg.Instruction.LOAD,
                                uses = set(),
                                uses_debug = [memslot])
                        
                        insert_after[pred.last_instr().id].append(load)
                        # TODO: if the last instruction in pred is br,
                        # insert it before br.

            else:
                replace = []
                for var in instr.uses:
                    if var.is_spilled_at(instr):
                        # Insert load before the instruction.
                        # [... = v1] -> [v2 = load mem(v1) ;  ... = v2]
                        v = f.get_or_create_variable()
                        memslot = var.alloc[instr.id]
                        replace.append((var, v))

                        
                        load = cfg.Instruction(
                                bb = instr.bb,
                                defn = v,
                                opname = cfg.Instruction.LOAD,
                                uses = [],
                                uses_debug = [memslot])

                        insert_before[instr.id].append(load)

                for (a, b) in replace:
                    instr.uses.remove(a)
                    instr.uses.add(b)

                    # Replace all occurrences in uses_debug.
                    for j, vd in enumerate(instr.uses_debug):
                        if vd == a:
                            instr.uses_debug[j] = b


    # Reewrite instructions.
    for bb in f.bblocks.values():
        new_instructions = []
        for instr in bb.instructions:
            for ib in insert_before[instr.id]:
                new_instructions.append(ib)
            new_instructions.append(instr)
            for ia in insert_after[instr.id]:
                new_instructions.append(ia)

        bb.set_instructions(new_instructions)

