class Spiller(object):
    def spill_variables(f, regcount):
        raise NotImplementedError()


class BeladySpiller(Spiller):
    # For every instruction and basic block we define the cost as minimal distance from the nearest use
    # of this variable. Variables used in phi instructions are treated as if they were used
    # at the end of the corresponding predecessor block. In case of basic blocks, this is minimal distance
    # from the end of the basic block.
    # Note that variables in loops are not processed precisely.
    def compute_cost(self, f, var):
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
        cost = {}
        for var in f.vars.values():
            cost[var] = self.compute_cost(f, var)

        # Spills variables from the given set of live variables, according to the Belady cost function.
        def spill_from_liveset(liveset, var_cost):
            not_spilled_live_in = liveset - to_spill
            
            if len(not_spilled_live_in) > regcount:
                # If register pressure is greater then regcount
                # we have to spill at least S = (#live_variables - regcount) variables.
                S = len(not_spilled_live_in) - regcount
                sorted_by_cost = sorted(not_spilled_live_in, key = lambda x: var_cost[x])[::-1]
                #print instr.num, sorted_by_cost, [cost[x][instr.id] for x in sorted_by_cost]
                for i in range(S):
                    to_spill.add(sorted_by_cost[i])
                    sorted_by_cost[i].spill()


        for bb in f.bblocks.values():
            for instr in bb.instructions:
                spill_from_liveset(instr.live_in, var_cost = {var: cost[var][instr.id] for var in instr.live_in})

            spill_from_liveset(bb.live_out, var_cost = {var: cost[var][bb.id] for var in bb.live_out})

        return to_spill


class BeladyWithLoopsSpiller(BeladySpiller):

    # For each variable, divide its belady metric by depth of the maximal loop it is
    # located in, taken over the whole program.
    def compute_cost(self, f, var):
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

        print "here", var
        ## Compute maximal loop depth
        max_ld = 1
        for bb in f.bblocks.values():
            for instr in bb.instructions:
                if not instr.is_phi():
                    if var in instr.uses:
                        max_ld = max(max_ld, instr.get_loop_depth())
        
#        print "max_ld", max_ld
        if max_ld > 1:
            for key in cost:
                cost[key] = cost[key]/max_ld
                print cost[key]

        return cost


def default():
    return BeladySpiller()
