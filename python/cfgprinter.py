import cfg
from termcolor import colored
import utils

class PrintOptions:
    def __init__(self, **options):
        self.colors = options.get("colors", True)
        self.llvm_names = options.get("llvm_names", False)
        self.nums = options.get("nums", True)
        self.predecessors = options.get("predecessors", False)
        self.successors = options.get("successors", False)
        self.uevs_defs = options.get("uevs_defs", False)
        self.liveness = options.get("liveness", False)
        self.dominance = options.get("dominance", False)
        self.intervals_verbose = options.get("intervals_verbose", False)
        self.intervals_advanced = options.get("intervals_advanced", False)
        self.show_spilled = options.get("show_spilled", False)
        # Instead of variable names print allocs.
        self.alloc_only = options.get("alloc_only", False)
        # Besides variable names print allocs.
        self.with_alloc = options.get("with_alloc", False)


# Here value is an object which has id and optional llvm_id
class ValuePrinter:
    def __init__(self, val, options=PrintOptions()):
        self.val = val
        self.options = options 

    def vid(self):
        return str(self.val.id)

    def full_name(self):
        llvm_name = self.val.llvm_name if self.val.llvm_name is not None else ""
        return self.vid() + "(" + llvm_name + ")"

    def __str__(self):
        if self.options.llvm_names:
            return self.full_name()
        
        return self.vid()

    def __repr__(self):
        return self.__str__()

def allocstr(alloc):
    if alloc is None:
        return None
    if utils.is_regname(alloc):
        return colored(alloc, 'blue')
    else:
        return colored(alloc, 'green')

class InstrPrinter:
    def __init__(self, instr, options=PrintOptions()):
        self.instr = instr
        self.options = options

    def defn(self):
        d = self.instr.definition
        if d is None:
            return None
        if self.options.llvm_names:
            vstr = ValuePrinter(d, self.options).full_name()
        else:
            vstr = ValuePrinter(d, self.options).vid()

        if self.options.colors:
            vstr = colored(vstr, 'yellow', attrs=['bold'])

        alloc = d.alloc[self.instr.id] if self.instr.id in d.alloc else None
        if self.options.alloc_only and alloc:
            vstr = allocstr(alloc)
        elif self.options.with_alloc and alloc:
            vstr += "("+allocstr(alloc)+")"

        return vstr


    def uses(self):
        res = ""
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

                res += str(bid) + " -> " + vstr + " "
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

                res += vstr + " " 

        return res

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

class BBPrinter:
    def __init__(self, bb, options=PrintOptions()):
        self.bb = bb
        self.options = options
        self.pattern = "{:>10}: {:>}"

    def instructions(self):
        res = ""
        for instr in self.bb.instructions:
            res += InstrPrinter(instr, self.options).full() + "\n"

        return res

    def predecessors(self):
        preds = [ValuePrinter(pred, self.options) for pred in list(self.bb.preds.values())]
        return self.pattern.format("PREDS", preds) 

    def successors(self):
        succs = [ValuePrinter(pred, self.options) for pred in list(self.bb.succs.values())]
        return self.pattern.format("SUCCS", succs)

    def uevs_defs(self):
        assert self.bb.uevs is not None and self.bb.defs is not None
        uevs =  [ValuePrinter(uev, self.options) for uev in list(self.bb.uevs)]
        defs = [ValuePrinter(defn, self.options) for defn in list(self.bb.defs)]
       
        return self.pattern.format("UEVS", uevs) + "\n" + \
               self.pattern.format("DEFS", defs) 

    def liveness(self):
        assert self.bb.live_in is not None and self.bb.live_out is not None
        live_in = [ValuePrinter(var, self.options) for var in list(self.bb.live_in)]
        live_out = [ValuePrinter(var, self.options) for var in list(self.bb.live_out)]
        
        return self.pattern.format("LIVE-IN", live_in) + "\n" + \
               self.pattern.format("LIVE-OUT", live_out) 

    def dominance(self):
        assert self.bb.dominators is not None
        dominators = [ValuePrinter(dom, self.options) for dom in list(self.bb.dominators)]
        return self.pattern.format("DOM", dominators) 


class FunctionPrinter:
    def __init__(self, f, options=PrintOptions()):
        self.f = f
        self.options = options
        
    def bbs(self):
        res = ""
#        sorted_bblocks = sorted(self.f.bblocks.values(), key=lambda bb: bb.id)
        bbs = utils.reverse_postorder(self.f)
        for bb in bbs:
            printer = BBPrinter(bb, self.options)
            bb_name = str(bb.id) + "(" + str(bb.llvm_name) + ")"
            bb_name = colored(bb_name, attrs=['underline'])
            res += bb_name + "\n" + printer.instructions()
            if self.options.predecessors:
                res += "\n" + printer.predecessors()
            if self.options.successors:
                res += "\n" + printer.successors()
            if self.options.uevs_defs:
                res += "\n" + printer.uevs_defs()
            if self.options.liveness:
                res += "\n" + printer.liveness()
            if self.options.dominance:
                res += "\n" + printer.dominance()

            res += "\n\n"
        return res

    def __str__(self):
        return self.bbs()


class IntervalsPrinter:
    def __init__(self, intervals, options=PrintOptions()):
        self.intervals = intervals
        self.options = options
        self.basic_pattern = "{:10s} {:10s}"
        self.reg_pattern = "{:^6s}"
        self.verbose_pattern = "{:10s} {:15s}"
        self.subs_pattern = "{}"


    def subinterval(self, subiv):
        endpoints = "[" + str(subiv.fr) + ", " + str(subiv.to) + "]"
        return endpoints


    def interval(self, iv):
        endpoints = "[" + str(iv.fr) + ", " + str(iv.to) + "]"
        basic = self.basic_pattern.format(endpoints, ValuePrinter(iv.var, self.options))
        reg = self.reg_pattern.format(iv.alloc if utils.is_regname(iv.alloc) else "-")

        res = [basic, reg]
        if self.options.intervals_verbose:
            defn = iv.defn.num if iv.defn else None
            uses = [use.num for use in iv.uses]
            verbose = self.verbose_pattern.format(str(defn), uses)
            res.append(verbose)

        if self.options.intervals_advanced:
            subs = [self.subinterval(sub) for sub in iv.subintervals]
            res.append(self.subs_pattern.format(' '.join(subs)))
            

        return ''.join(res)

    def full(self):
        ivs = []
        for ivlist in self.intervals.values():
            ivs.extend(ivlist)
        
        ivs = sorted(ivs, key=lambda iv: (iv.fr, iv.to))

        res = self.basic_pattern.format("INTERVAL", "VAR-ID") + self.reg_pattern.format("REG")
        if self.options.intervals_verbose:
            res += self.verbose_pattern.format("DEF", "USES")
        if self.options.intervals_advanced:
            res += self.subs_pattern.format("SUBINTERVALS")
        res += "\n"

        for iv in ivs:
            if not iv.empty():
                res += self.interval(iv) + "\n"

        return res + "\n"
            

class CostPrinter:
    def __init__(self, f, cost_calc):
        self.f = f
        self.num_pattern = "{:^5}"
        self.ld_pattern = "{:^8}"
        self.cost_pattern = "{:^10}"
        self.instr_pattern = "{:^30}"
        self.cost_calc = cost_calc

    def full(self):
        bbs = utils.reverse_postorder(self.f)
        # if no numbers, number
        instructions = []
        for bb in bbs:
           instructions.extend(bb.instructions)

        instructions = sorted(instructions, key = lambda i: i.num)
        res = self.ld_pattern.format("LOOP") + \
                self.cost_pattern.format("COST") + self.instr_pattern.format("INSTR") + "\n"

        for i in instructions:
            cost = self.cost_calc.instr_cost(i)
            istr = InstrPrinter(i, PrintOptions(alloc_only=True)).full()
            line = self.ld_pattern.format(i.get_loop_depth()) + \
                    self.cost_pattern.format(cost) + self.instr_pattern.format(istr) + "\n"
            res += line

        return res
