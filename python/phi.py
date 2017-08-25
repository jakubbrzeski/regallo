import utils
import cfg

# A helper class storing any value plus its allocation (register or mem slot).
class Alloc:
    def __init__(self, val, alloc):
        self.val = val
        self.alloc = alloc

# loclist of defs and uses wrapped together with corresponding registers.
def order_moves(loclist):
    results = []

    # Building graph.
    class Edge:
        def __init__(self, d, u):
            self.d = d
            self.u = u

    IN = {}
    OUT = {}

    # Initialize.
    for (d,u) in loclist:
        IN[d.alloc] = set()
        IN[u.alloc] = set()
        OUT[d.alloc] = set()
        OUT[u.alloc] = set()

    for (d,u) in loclist:
        e = Edge(d,u)
        if d.alloc != u.alloc: # Exlude self-loops.
            IN[d.alloc].add(e)
            OUT[u.alloc].add(e)

    # Find edges (a,b): outdeg(b) == 0.
    leaves = []
    for alloc, edges in OUT.iteritems():
        for edge in edges:
            if not OUT[edge.d.alloc]:
                leaves.append(edge)

    # Iteratively cut edges from leaves list.
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

    # Now the graph is either empty or contains cycles.
    for alloc, edges in IN.iteritems():
        if edges:
            e = edges.pop()
            l = [e]
            while e.u.alloc != alloc:
                e = IN[e.u.alloc].pop()
                l.append(e)
            
            # None means that we have to put here a temporary variable
            # with scratch register.
            results.append((None, l[0].u))
            results.extend([(e.d, e.u) for e in l[1:]])
            results.append((l[0].d, None))

    return results

# Inserts given moves at the end of the basic block.
# Moves is a list of pairs (Alloc(def), Alloc(use))
def insert_moves(bb, moves):
    instructions = []
    for (d,u) in moves:
        # If d or u is None it means we need to use a temporary variable.
        # See function 'order_moves(moves)' for details.
        if d is None:
            d = Alloc(bb.f.temp_variable(), utils.scratch_reg())
        if u is None:
            u = Alloc(bb.f.temp_variable(), utils.scratch_reg())

        # There are four cases
        if utils.is_regname(d.alloc) and utils.is_regname(u.alloc):
            # 1) Both d and u are in registers => produce "d = u"
            instr = cfg.Instruction(bb, d.val, cfg.Instruction.MOV, [u.val], [u.val])
            instructions.append(instr)
            d.val.alloc[instr.id] = d.alloc
            u.val.alloc[instr.id] = u.alloc

        elif utils.is_slotname(d.alloc) and utils.is_slotname(u.alloc):
            # 2) Both are in memory slot => produce:
            # temp = load slot(u)
            # store slot(d) <- temp
            tvar = bb.f.temp_variable()
            load = cfg.Instruction(bb, tvar, cfg.Instruction.LOAD, [], [u.alloc])
            store = cfg.Instruction(bb, None, cfg.Instruction.STORE, [tvar], [d.alloc, tvar])
            instructions.extend([load, store])

        elif utils.is_slotname(d.alloc) and utils.is_regname(u.alloc):
            # 3) d is in memory slot, u in register => produce "store slot(d) <- u"

            instr = cfg.Instruction(bb, None, cfg.Instruction.STORE, [u.val], [d.alloc, u.val])
            instructions.append(instr)
            u.val.alloc[instr.id] = u.alloc

        else:
            # 4) d is in register, u is in memory slot => produce "d = load slot(u)"
            instr = cfg.Instruction(bb, d.val, cfg.Instruction.LOAD, [], [u.alloc])
            instructions.append(instr)
            d.val.alloc[instr.id] = d.alloc

       
    bb.instructions.extend(instructions)


# Eliminates phi functions for the given basic block. It assumes that
# variables already have registers or memory slots assigned.
# WARNING: it breaks instruction numbering; uevs, defs and liveness sets;
#          basic block dominance and loop information.
def eliminate_phi_in_bb(bb):
    if not bb.phis:
        return

    for pred in bb.preds.values():
        moves = []
        for phi in bb.phis:
            d = Alloc(phi.definition, phi.definition.alloc[phi.id])
            u = Alloc(phi.uses[pred.id], phi.uses[pred.id].alloc[phi.id])
            moves.append((d,u))

        moves = order_moves(moves)
       
        # Normally we would insert moves in this predeccessor but if it has
        # more than one successor, we have to add a new basic block on the edge
        # from pred to bb.
        bti = pred
        if len(pred.succs) > 1:
            bid = "bb" + str(len(bb.f.bblocks) + 1) # New id.
            bti = cfg.BasicBlock(bid, bb.f)
            # Add edge pred-bti 
            bti.preds[pred.id] = pred
            pred.succs[bti.id] = bti
            # Add edge bti-bb
            bti.succs[bb.id] = bb
            bb.preds[bti.id] = bti
            # Update in the function.
            bb.f.bblocks[bti.id] = bti
            # Delete edge (pred, bb).
            del bb.preds[pred.id]
            del pred.succs[bb.id]

        insert_moves(bti, moves)

    bb.instructions = bb.instructions[len(bb.phis):]
    bb.phis = []

# Eliminates PHI instructions throughout the whole function.
# WARNING: it breaks  uevs, defs and liveness sets;
#          basic block dominance and loop information.
def eliminate_phi(f):
    for bb in f.bblocks.values():
        eliminate_phi_in_bb(bb)

    utils.number_instructions(utils.reverse_postorder(f))

