import cfg
from termcolor import colored
import utils

class Opts:
    def __init__(self, **options):
        self.colors = options.get("colors", True)
        self.llvm_names = options.get("llvm_names", False)
        self.nums = options.get("nums", True)
        
        self.predecessors = options.get("predecessors", False)
        self.successors = options.get("successors", False)
        self.defs_uevs = options.get("defs_uevs", False)
        self.reg_defs_uevs = options.get("reg_defs_uevs", False)
        self.defs_uevs_with_alloc = options.get("defs_uevs_with_alloc", False)

        self.liveness = options.get("liveness", False)
        self.reg_liveness = options.get("reg_liveness", False)
        self.liveness_with_alloc = options.get("liveness_with_alloc", False)

        self.dominance = options.get("dominance", False)
        # Instead of variable names, print allocs.
        self.alloc_only = options.get("alloc_only", False)
        # Besides variable names, print allocs.
        self.with_alloc = options.get("with_alloc", False)
        
        self.intervals_verbose = options.get("intervals_verbose", False)
        self.subintervals = options.get("subintervals", False)


# Here value is an object which has id and optional llvm_id
class ValueString:
    def __init__(self, val, options=Opts()):
        self.val = val
        self.options = options 

    def vid(self):
        return str(self.val.id)

    def full_name(self):
        llvm_name = self.val.llvm_name if self.val.llvm_name is not None else ""
        return self.vid() + "(" + llvm_name + ")"

    def __str__(self):
        if self.val is None:
            return "None"

        if isinstance(self.val, cfg.Variable) or isinstance(self.val, cfg.BasicBlock):
            if self.options.llvm_names:
                return self.full_name()
            
            return self.vid()

        else:
            return self.val

    def __repr__(self):
        return self.__str__()

def allocstr(alloc):
    if alloc is None:
        return None
    if utils.is_regname(alloc):
        return colored(alloc, 'blue')
    else:
        return colored(alloc, 'green')

class InstrString:
    def __init__(self, instr, options=Opts()):
        self.instr = instr
        self.options = options

    def defn(self):
        d = self.instr.definition
        if d is None:
            return None
        if self.options.llvm_names:
            vstr = ValueString(d, self.options).full_name()
        else:
            vstr = ValueString(d, self.options).vid()

        if self.options.colors:
            vstr = colored(vstr, 'yellow', attrs=['bold'])

        alloc = d.alloc[self.instr.id] if self.instr.id in d.alloc else None
        if self.options.alloc_only and alloc:
            vstr = allocstr(alloc)
        elif self.options.with_alloc and alloc:
            vstr += "("+allocstr(alloc)+")"

        return vstr


    def uses(self):
        res = []

        if self.instr.is_phi():
            for (bid, var) in self.instr.uses_debug.iteritems():
                if isinstance(var, cfg.Variable):
                    vstr = colored(var, 'yellow')
                    alloc = var.alloc[self.instr.id] if self.instr.id in var.alloc else None
                    if self.options.alloc_only and alloc:
                        vstr = allocstr(alloc)
                    elif self.options.with_alloc and alloc:
                        vstr += "("+allocstr(alloc)+")"

                elif utils.is_slotname(var) and (self.options.alloc_only 
                        or self.options.with_alloc):
                    vstr = colored(var, 'green')

                else:
                    vstr = var

                res.extend([str(bid), " -> ", vstr, " "])
        else:
            for var in self.instr.uses_debug:
                if isinstance(var, cfg.Variable):
                    vstr = colored(var, 'yellow', attrs=['bold'])
                    alloc = var.alloc[self.instr.id] if self.instr.id in var.alloc else None
                    if self.options.alloc_only and alloc:
                        vstr = allocstr(alloc)
                    elif self.options.with_alloc and alloc:
                        vstr += "("+allocstr(alloc)+")"

                elif utils.is_slotname(var) and (self.options.alloc_only 
                        or self.options.with_alloc):
                    vstr = colored(var, 'green')

                else:
                    vstr = var

                res.extend([vstr, " "])

        return ''.join(res)

    def full(self):
        num = str(self.instr.num) + ":" if self.options.nums and self.instr.num is not None else ">"
        opname = colored(self.instr.opname, 'red')
        if self.instr.is_phi():
            opname = colored(self.instr.opname, 'red')

        defn = self.defn()

        if not defn:
            return "{:>4} {:^6} {:<20}".format(num, opname, self.uses())

        return "{:>4} {:>4} = {:^6} {:<20}".format(
                num, 
                defn,
                opname,
                self.uses())

    def __str__(self):
        return self.full()

class BBString:
    def __init__(self, bb, options=Opts()):
        self.bb = bb
        self.options = options
        self.pattern = "{:>10}: {:>}"

    def instructions(self):
        res = []
        for instr in self.bb.instructions:
            if self.options.alloc_only and instr.is_redundant():
                continue

            res.append(InstrString(instr, self.options).full())

        return "\n".join(res)

    def predecessors(self):
        preds = [ValueString(pred, self.options) for pred in list(self.bb.preds.values())]
        return self.pattern.format("PREDS", preds) 

    def successors(self):
        succs = [ValueString(pred, self.options) for pred in list(self.bb.succs.values())]
        return self.pattern.format("SUCCS", succs)

    def defs_uevs(self):
        assert self.bb.uevs is not None and self.bb.defs is not None
        uevs =  [ValueString(uev, self.options) for uev in list(self.bb.uevs)]
        defs = [ValueString(defn, self.options) for defn in list(self.bb.defs)]
       
        return self.pattern.format("UEVS", uevs) + "\n" + \
               self.pattern.format("DEFS", defs) 

    def reg_defs_uevs(self):
        assert self.bb.reg_uevs is not None and self.bb.reg_defs is not None
        uevs =  [ValueString(reg, self.options) for reg in list(self.bb.reg_uevs)]
        defs = [ValueString(reg, self.options) for reg in list(self.bb.reg_defs)]
       
        return self.pattern.format("REG-UEVS", uevs) + "\n" + \
               self.pattern.format("REG-DEFS", defs) 

    def defs_uevs_with_alloc(self):
        assert self.bb.uevs_with_alloc is not None and self.bb.defs_with_alloc is not None
        uevs = [(ValueString(v, self.options), ValueString(al, self.options)) for (v, al) in self.bb.uevs_with_alloc.iteritems()]
        defs = [(ValueString(v, self.options), ValueString(al, self.options)) for (v, al) in self.bb.defs_with_alloc.iteritems()]
      
        return self.pattern.format("UEVS-ALLOC", uevs) + "\n" + \
               self.pattern.format("DEFS-ALLOC", defs) 

    def liveness(self):
        assert self.bb.live_in is not None and self.bb.live_out is not None
        live_in = [ValueString(var, self.options) for var in list(self.bb.live_in)]
        live_out = [ValueString(var, self.options) for var in list(self.bb.live_out)]
        
        return self.pattern.format("LIVE-IN", live_in) + "\n" + \
               self.pattern.format("LIVE-OUT", live_out) 

    def reg_liveness(self):
        assert self.bb.reg_live_in is not None and self.bb.reg_live_out is not None
        live_in = [ValueString(reg, self.options) for reg in list(self.bb.reg_live_in)]
        live_out = [ValueString(reg, self.options) for reg in list(self.bb.reg_live_out)]
        return self.pattern.format("REG-LIVE-IN", live_in) + "\n" + \
               self.pattern.format("REG-LIVE-OUT", live_out) 

    def liveness_with_alloc(self):
        assert self.bb.live_in_with_alloc is not None and self.bb.live_out_with_alloc is not None
        live_in = [(ValueString(v, self.options), ValueString(al, self.options)) for (v, al) in self.bb.live_in_with_alloc.iteritems()]
        live_out = [(ValueString(v, self.options), ValueString(al, self.options)) for (v, al) in self.bb.live_out_with_alloc.iteritems()]
        return self.pattern.format("LIVE-IN-ALLOC", live_in) + "\n" + \
               self.pattern.format("LIVE-OUT-ALLOC", live_out) 

    def dominance(self):
        assert self.bb.dominators is not None
        dominators = [ValueString(dom, self.options) for dom in list(self.bb.dominators)]
        return self.pattern.format("DOM", dominators) 


class FunctionString:
    def __init__(self, f, options=Opts()):
        self.f = f
        self.options = options
        
    def bbs(self):
        res = []
        bbs = utils.reverse_postorder(self.f)
        for bb in bbs:
            if self.options.alloc_only and bb.is_redundant():
                continue

            printer = BBString(bb, self.options)
            bb_name = str(bb.id) + "(" + str(bb.llvm_name) + ")"
            bb_name = colored(bb_name, attrs=['underline'])
            res.append(bb_name)
            res.append(printer.instructions())
            if self.options.predecessors:
                res.append(printer.predecessors())
            if self.options.successors:
                res.append(printer.successors())
            if self.options.defs_uevs:
                res.append(printer.defs_uevs())
            if self.options.reg_defs_uevs:
                res.append(printer.reg_defs_uevs())
            if self.options.defs_uevs_with_alloc:
                res.append(printer.defs_uevs_with_alloc())
            if self.options.liveness:
                res.append(printer.liveness())
            if self.options.liveness_with_alloc:
                res.append(printer.liveness_with_alloc())
            if self.options.dominance:
                res.append(printer.dominance())
            if self.options.reg_liveness:
                res.append(printer.reg_liveness())
            res.append("\n")

        return "\n".join(res)

    def __str__(self):
        return self.bbs()


class IntervalsString:
    def __init__(self, intervals, options=Opts()):
        self.intervals = intervals
        self.options = options
        self.basic_pattern = "{:20s} {:10s}"
        self.reg_pattern = "{:^10s}"
        self.verbose_pattern = "{:10s} {:15s}"
        self.subs_pattern = "{}"


    def subinterval(self, subiv):
        endpoints = "[" + str(subiv.fr) + ", " + str(subiv.to) + "]"
        return endpoints


    def interval(self, iv):
        endpoints = "[" + str(iv.fr) + ", " + str(iv.to) + "]"
        basic = self.basic_pattern.format(endpoints, ValueString(iv.var, self.options))
        reg = self.reg_pattern.format(iv.alloc if utils.is_regname(iv.alloc) else "-")

        res = [basic, reg]
        if self.options.intervals_verbose:
            defn = iv.defn.num if iv.defn else None
            uses = [use.num for use in iv.uses]
            verbose = self.verbose_pattern.format(str(defn), uses)
            res.append(verbose)

        if self.options.subintervals:
            subs = [self.subinterval(sub) for sub in iv.subintervals]
            res.append(self.subs_pattern.format(' '.join(subs)))
            

        return ''.join(res)

    def full(self):
        ivs = []
        for ivlist in self.intervals.values():
            ivs.extend(ivlist)
        
        ivs = sorted(ivs, key=lambda iv: (iv.fr, iv.to))

        res = [self.basic_pattern.format("INTERVAL", "VAR-ID"), self.reg_pattern.format("REG")]
        if self.options.intervals_verbose:
            res.append(self.verbose_pattern.format("DEF", "USES"))
        if self.options.subintervals:
            res.append(self.subs_pattern.format("SUBINTERVALS"))
        res.append("\n")

        for iv in ivs:
            if not iv.empty():
                res.extend([self.interval(iv), "\n"])

        res.append("\n")
        return ''.join(res)

    def __str__(self):
        return self.full()
            

class CostString:
    def __init__(self, f, cost_calc):
        self.f = f
        self.num_pattern = "{:^5}"
        self.ld_pattern = "{:^8}"
        self.cost_pattern = "{:^10}"
        self.instr_pattern = "{:^30}"
        self.cost_calc = cost_calc

    def full(self):
        res = [self.cost_calc.name]
        bbs = utils.reverse_postorder(self.f)
        # if no numbers, number
        instructions = []
        for bb in bbs:
           instructions.extend(bb.instructions)

        instructions = sorted(instructions, key = lambda i: i.num)
        line = ''.join([
            self.ld_pattern.format("LOOP"),
            self.cost_pattern.format("COST"),
            self.instr_pattern.format("INSTR")])

        res.append(line)

        csum = 0
        for i in instructions:
            cost = self.cost_calc.instr_cost(i)
            csum += cost

            istr = InstrString(i, Opts(alloc_only=True)).full()
            line = ''.join([
                    self.ld_pattern.format(i.get_loop_depth()),
                    self.cost_pattern.format(cost),
                    self.instr_pattern.format(istr)])

            res.append(line)

        summary = "SUM: " + str(csum)
        res.append(summary)
        res.append("\n")

        return "\n".join(res)

    def __str__(self):
        return self.full()
