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
def insert_moves(bb, moves, regcount=0):
    new_instructions = []
    
    all_regs = utils.RegisterSet(regcount).free
    reg_defs = set() 

    for (d,u) in moves:
        if utils.is_regname(d.alloc): 
            reg_defs.add(d.alloc)

            # REG - CONST
            if u.alloc is None:
                instr = cfg.Instruction(bb, d.val, cfg.Instruction.MOV, [], [u.val])
                new_instructions.append(instr)
           
            # REG - REG
            elif utils.is_regname(u.alloc):
                instr = cfg.Instruction(bb, d.val, cfg.Instruction.MOV, [u.val], [u.val])
                new_instructions.append(instr)

            # REG - MEM
            elif utils.is_slotname(u.alloc):
                instr = cfg.Instruction(bb, d.val, cfg.Instruction.LOAD, [], [u.val])
                new_instructions.append(instr)

        elif utils.is_slotname(d.alloc):
            # MEM - CONST
            if u.alloc is None:
                instr = cfg.Instruction(bb, None, cfg.Instruction.STORE, [], [d.val, u.val])
                new_instructions.append(instr)

            # MEM - REG
            elif utils.is_regname(u.alloc):
                instr = cfg.Instruction(bb, None, cfg.Instruction.STORE, [u.val], [d.val, u.val])
                new_instructions.append(instr)

            # MEM - MEM
            elif utils.is_slotname(u.alloc):
                occupied_regs = set(var.alloc for var in bb.live_out) | reg_defs
                free_regs = all_regs - occupied_regs
                if not free_regs:
                    return False

                tmp = bb.f.get_or_create_variable()
                tmp.alloc = free_regs.pop()
                load = cfg.Instruction(bb, tmp, cfg.Instruction.LOAD, [], [u.alloc])
                store = cfg.Instruction(bb, None, cfg.Instruction.STORE, [tmp], [d.alloc, tmp])

                new_instructions.append(load)
                new_instructions.append(store)

                #return False


    bb.instructions.extend(new_instructions)
    return True


def insert_cycles(bb, cycles):
    endpoints = []
    for cycle in cycles:
        instructions = []
        tmp = bb.f.get_or_create_variable()
        i1, i2 = None, None # endpoints of the cycle
        cycle_allocs = set()
        for (d,u) in cycle:
            instr = None
            if d is None:
                instr = cfg.Instruction(bb, tmp, cfg.Instruction.MOV, [u.val], [u.val])
                i1 = instr
            elif u is None:
                instr = cfg.Instruction(bb, d.val, cfg.Instruction.MOV, [tmp], [tmp])
                cycle_allocs.add(d.alloc)
                i2 = instr
            else:
                instr = cfg.Instruction(bb, d.val, cfg.Instruction.MOV, [u.val], [u.val])
                cycle_allocs.add(d.alloc)

            instructions.append(instr)

        bb.instructions.extend(instructions)
        endpoints.append((i1, i2, cycle_allocs))

    return endpoints

# If during phi elimination a cycle of movs appears - it
# is cut by storing one of its variables in a new temporary variable.
# This function takes two instructions being the endpoints of a list of
# mov instructions that was created from the cut cycle and checks whether
# this temporary variable can be assigned a register or must be replaced
# by STORE and LOAD operations. Cycle may occur only between registers.
#
# regcount - overall number of registers available. If 0, we replace temp. var by STORE and LOAD.
def allocate_cycle(i1, i2, cycle_allocs, regcount=0):
    # We want to find a free register between i1 and i2. 
    # [i1, i2] is a connected interval.
   
    if regcount:
        regset = utils.RegisterSet(regcount)
        # registers live out at the end of the cycle
        live_out_regs = set([var.alloc for var in i2.live_out if utils.is_regname(var.alloc)])
        occupied = cycle_allocs | live_out_regs
        free = regset.free - occupied
        if free:
            i1.definition.alloc = free.pop() 
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
# The algorithm is as follows:
# 1. For each basic block:
#    - we collect all potential variable moves that need to be inserted
#      on a particular predecessor edge.
#    - we order these moves in a proper way to preserve the correct data
#      flow between registers. We store the ordered moves and cycles
#      separately since they need different treatment. We will insert them
#      later
#    - if a predecessor of the current basic block has multiple successors,
#      we need to put a new basic block on their edge.
#
# 2. We recompute liveness sets because of newly created basic blocks and
#    then insert all previously registered moves and cycles independently.
#    
#    Cycles have to be cut by inserting an additional variable or spilling
#    one variable in the cycle into memory. Here we create the temporary
#    variable for each cycle but try to allocate it at the end of the procedure.
#   
#    Memory-to-memory moves need an additional variable and register - so
#    if there is no free register, we have to return False here.
#
# 3. When all moves and cycles were properly inserted, we remove phi instructions
#    from all basic blocks and execute liveness analysis again beause we
#    need up-to-date liveness information in the next step.
#
# 4. At the end, we go back to cycles and try to allocate the new variables.
#    If there are no free registers at the program points where cycle is located,
#    we remove the temporary variable and spill one of cycle's original variables
#    into memory.
#    
# regcount - overall number of available registers: phi elimination may 
#            need additional when dealing with memory to memory copies
#            or in case of mov-cycles.
def eliminate_phi(f, regcount=0):


    # List of tuples (instr1, instr2, allocs) denoting start and end instruction
    # where a particular cycle was inserted and set of registers allocated to
    # all variables on the cycle.
    cycles_endpoints = []

    # List of tuples (basic block, moves, cycles) denoting the need to insert 
    # moves and cycles at the end of the given basic block. We register such
    # events and before executing them we perform full liveness analysis which
    # is necessary for moves and cycles insertion espcially in case of newly
    # created basic blocks.
    events = []

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
                d = Alloc(phi.definition, phi.definition.alloc)
                u = Alloc(phi.uses_debug[pred.id], None)
                if pred.id in phi.uses:
                    u = Alloc(phi.uses[pred.id], phi.uses[pred.id].alloc)
                moves.append((d,u))
            
            moves, cycles = order_moves(moves)
            if moves or cycles:
                # It may happen that moves or cycles are empty,
                # e.g. if there were self loops only.
                # If predecessor has more than one successor, we have to add
                # a new basic block on the edge from pred to bb.
                bti = pred
                if len(pred.succs) > 1:
                    bti = f.create_new_basic_block()
                    f.insert_basic_block_between(bti, pred, bb)
     
                events.append((bti, moves, cycles))    
    
    # Functions repsonsible for inserting moves need up-to-date liveness information
    # which might have been disturbed if we added new basic blocks.
    f.perform_liveness_analysis()
       
    # Now insert moves and cycles.
    for (bti, moves, cycles) in events:     
        if moves:
            success = insert_moves(bti, moves, regcount)
            if not success:
                # It can fail because of lack or available registers in mem-mem copies.
                return False

        if cycles:
            endpoints = insert_cycles(bti, cycles)
            cycles_endpoints.extend(endpoints)

    for bb in f.bblocks.values():
        # Remove phi instructions from this block.
        bb.instructions = [instr for instr in bb.instructions if not instr.is_phi()]
        bb.phis = []

    # After changes in instructions sets, we perform liveness analysis again.
    f.perform_liveness_analysis()

    for (i1, i2, allocs) in cycles_endpoints:
        allocate_cycle(i1, i2, allocs, regcount)

    return True

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
            # Variable instances used and defined in phi instructions are treated
            # separately in phi elimination phase.
            if not instr.is_phi():
                # DEFINITION
                if instr.definition and instr.definition.is_spilled():
                    # Insert store after instr.
                    # [v1 = ...] -> [v2 = ... ; store mem(v1), v2]  
                    v = f.get_or_create_variable()
                    memslot = instr.definition.alloc
                    instr.definition = v
                    
                    store = cfg.Instruction(
                            bb = instr.bb, 
                            defn = None, 
                            opname = cfg.Instruction.STORE,
                            uses = set([v]), 
                            uses_debug = [memslot, v])

                    insert_after[instr.id].append(store)
               
                # USES
                replace = []
                for var in instr.uses:
                    if var.is_spilled():
                        # Insert load before the instruction.
                        # [... = v1] -> [v2 = load mem(v1) ;  ... = v2]
                        v = f.get_or_create_variable()
                        memslot = var.alloc
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
            if instr.id in insert_before:
                for ib in insert_before[instr.id]:
                    new_instructions.append(ib)
            new_instructions.append(instr)
            if instr.id in insert_after:
                for ia in insert_after[instr.id]:
                    new_instructions.append(ia)

        bb.set_instructions(new_instructions)
   
    f.perform_full_analysis()
