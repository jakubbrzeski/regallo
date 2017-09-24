class Spiller(object):
    def spill_variables(f, regcount):
        raise NotImplementedError()


class BeladySpiller(Spiller):
    # For every instruction and basic block we define the cost as minimal distance from the nearest use
    # of this variable. Variables used in phi instructions are treated as if they were used
    # at the end of the corresponding predecessor block. In case of basic blocks, this is minimal distance
    # from the end of the basic block.
    # Note that variables in loops are not processed precisely.
    def compute_belady_cost(self, f, var):
        infinity = f.instr_counter
        cost = {iid: infinity for iid in range(f.instr_counter)}
        visited = set()
        processed = set()

        def dfs(bb):
            visited.add(bb.id)
            # Minimal cost computed over successors.
            last_cost = infinity
            for s in bb.succs.values():
                if s.id not in visited:
                    dfs(s)

                last_cost = min(last_cost, cost[s.first_instr().id])
                for phi in s.phis:
                    if bb.id in phi.uses and phi.uses[bb.id] == var:
                        last_cost = 0
                        break

            # basic block ids are different than instruction ids
            cost[bb.id] = last_cost
            for instr in reversed(bb.instructions):
                is_used_here = False
                if not instr.is_phi():
                    is_used_here = (var in instr.uses)

                if is_used_here:
                    cost[instr.id] = 0
                elif var in instr.live_out:
                    cost[instr.id] = 1 + last_cost
                else:
                    cost[instr.id] = infinity

                last_cost = cost[instr.id]

            processed.add(bb)

        dfs(f.entry_bblock)
        return cost


    def spill_variables(self, f, regcount):
        to_spill = set()
        belady_cost = {}
        for var in f.vars.values():
            belady_cost[var] = self.compute_belady_cost(f, var)

        # Spills variables from the given set of live variables, according to the Belady cost function.
        def spill_from_liveset(liveset, var_cost):
            not_spilled_live_in = liveset - to_spill
            
            if len(not_spilled_live_in) > regcount:
                # If register pressure is greater then regcount
                # we have to spill at least S = (#live_variables - regcount) variables.
                S = len(not_spilled_live_in) - regcount
                sorted_by_cost = sorted(not_spilled_live_in, key = lambda x: var_cost[x])[::-1]
                #print instr.num, sorted_by_cost, [belady_cost[x][instr.id] for x in sorted_by_cost]
                for i in range(S):
                    to_spill.add(sorted_by_cost[i])
                    sorted_by_cost[i].spill()


        for bb in f.bblocks.values():
            for instr in bb.instructions:
                spill_from_liveset(instr.live_in, var_cost = {var: belady_cost[var][instr.id] for var in instr.live_in})

            spill_from_liveset(bb.live_out, var_cost = {var: belady_cost[var][bb.id] for var in bb.live_out})

        return to_spill



def default():
    return BeladySpiller()
