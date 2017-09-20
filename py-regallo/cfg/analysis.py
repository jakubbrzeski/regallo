import utils
from cfg import Loop, Function, Module

###############################################################################
################################### LIVENESS ##################################
###############################################################################

# Computes sets of defined and upward-exposed variables
def compute_defs_and_uevs(bb):
    defs = set()
    uevs = set()

    for instr in bb.instructions:
        if not instr.is_phi():
            for var in instr.uses:
                if var not in defs:
                    uevs.add(var)
    
        if instr.definition:
            defs.add(instr.definition)

    bb.defs = defs
    bb.uevs = uevs

# Liveness analysis for instructions.
def perform_instr_liveness_analysis(bb, check_correctness=False):
    current_live_set = bb.live_out.copy()

    for instr in bb.instructions[::-1]:
        instr.live_out = current_live_set.copy()

        if instr.definition:
            var = instr.definition
            if var in current_live_set:
                current_live_set.remove(var)

        if not instr.is_phi(): # ?
            for var in instr.uses:
                current_live_set.add(var)

        instr.live_in = current_live_set.copy()

# For each basic block in the function and their instructions computes 
# liveness sets: live_in and live_out - sets of live-in and live-out variables
#
# Params:
# ordered_bbs - optional list of ordered basic blocks the analysis should be performed on.
def perform_liveness_analysis(f, ordered_bbs = None):
    for bb in f.bblocks.values():
        compute_defs_and_uevs(bb)
        bb.live_in = set()
        bb.live_out = set()

    if ordered_bbs is None:
        ordered_bbs = f.bblocks.values()

    change = True
    while change:
        change = False
        for bb in ordered_bbs:
            live_out_size = len(bb.live_out)
            for succ in bb.succs.values():
                bb.live_out |= (succ.live_in)
                # We add to the live-out set the input variables of phi instructions,
                # and remove their output variables.
                for phi in succ.phis:
                    if bb.id in phi.uses: # it may not be in there if the used value is not Variable.
                        if not phi.definition.is_spilled() and phi.definition in bb.live_out:
                            bb.live_out.remove(phi.definition)
                        if not phi.uses[bb.id].is_spilled():
                            bb.live_out.add(phi.uses[bb.id])
            
            live_in_size = len(bb.live_in)
            # Variable is in live-in set if
            # - it is upword-exposed in bb (i.e. used before any redefinition)
            # - or is live on the exit from bb and not defined in this block.
            # - or is defined by phi instruction.
            phi_defs = set([phi.definition for phi in bb.phis if phi.definition and not phi.definition.is_spilled()])
            maybe_live_in = (bb.uevs | (bb.live_out - bb.defs) | phi_defs)
            bb.live_in = set([v for v in maybe_live_in if not v.is_spilled()])

            if len(bb.live_in) > live_in_size or len(bb.live_out) > live_out_size:
                change = True

    for bb in ordered_bbs:
        perform_instr_liveness_analysis(bb) # updates liveness for each instruction.

###############################################################################
################################## DOMINANCE ##################################
###############################################################################

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


###############################################################################
#################################### LOOPS ####################################
###############################################################################

# Finds all Loops in this function.
def perform_loop_analysis(f):
    loops = []
    def find_loop((bb_end, bb_start)):
        if bb_start in bb_end.dominators:
            body = []
            def vpre(bb):
                body.append(bb)
            utils.dfs(bb_end, visited=set(), backwards=True, vpre=vpre, vstop=bb_start)
            loops.append(Loop(bb_start, bb_end, body[::-1])) 

    utils.dfs(f.entry_bblock, visited=set(), ef=find_loop)
    
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

    f.loops = loops

###############################################################################
###############################################################################
###############################################################################

def perform_full_analysis(obj):
    if isinstance(obj, Function):
        utils.number_instructions(utils.reverse_postorder(obj))
        perform_liveness_analysis(obj)
        perform_dominance_analysis(obj)
        perform_loop_analysis(obj)

    elif isinstance(obj, Module):
        for f in obj.functions.values():
            perform_full_analysis(f)
