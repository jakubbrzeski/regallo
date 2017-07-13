#include <iostream>
#include <cstring>
#include <fstream>
#include <sstream>
#include <map>

#include "llvm/Pass.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Value.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/IR/ModuleSlotTracker.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/Casting.h"
#include "llvm/IR/CFG.h"
#include "llvm/IR/Instructions.h"

#include "json.hpp"

// for convenience
using json = nlohmann::json;

using namespace llvm;
using std::cout;
using std::map;
using std::endl;

static cl::opt<std::string> ToJson("print-json-to-file", cl::desc("Expects a filename where the CFG as json will be printed."), cl::init(""));
static cl::opt<bool> PrintOut("print-out", cl::desc("Prints the CFG to the stdout."), cl::init(false));

namespace {

    const std::string SEPARATOR = "/";

    struct ControlFlowExtractor : public FunctionPass {
    private:
        class SlotMap {
            private:
                map<void*, int> M;
                int index = 0;
                const std::string PREFIX;
            public:
                SlotMap(const std::string& prefix) : PREFIX(prefix) {}

                std::string getSlotID(void* addr) {
                    auto it = M.find(addr);
                    int slot;
                    if (it != M.end()) slot = (it)->second; 
                    else {
                        slot = ++index;
                        M.insert(std::pair<void*, int>(addr, slot));
                    }
                    return PREFIX + std::to_string(slot);
                }
        } regMap, bbMap;

        std::string getSlotAndName(Value *val, SlotMap& map) {
            bool global = isa<GlobalValue>(val);
            std::string slotID = map.getSlotID(&(*val));
            std::string gl = global ? "G" : "L";
            std::string name = slotID + SEPARATOR;
            if (val->hasName()) name = name + (std::string)val->getName();
            name = name + SEPARATOR + gl;
            return name;
        }
        
        std::ofstream jsonOutputStream;
        std::ostringstream prettyOutputStream;
        typedef std::pair<std::string, std::string> strpair;
        json functionsJson;

    public:
        static char ID;

        ControlFlowExtractor() : FunctionPass(ID), regMap("v"), bbMap("bb") {
            if (!ToJson.empty()) {
               jsonOutputStream = std::ofstream(ToJson); 
            } 
        }

        bool runOnFunction(Function &F) override {
            std::string fname = F.getName();
            prettyOutputStream << "* * * Function: " << fname << " * * *" << endl;

            json functionJson = json::object();
            functionJson["name"] = fname;

            std::string entry_bb = getSlotAndName(&F.getEntryBlock(), bbMap);
            functionJson["entry_block"] = entry_bb;
            prettyOutputStream << "Entry Block: " << entry_bb << endl;

            /*
             * BASIC BLOCKS 
             */
            json bblocksJson = json::array();
            for (auto &Bb : F.getBasicBlockList()) {
                std::string bbName = getSlotAndName(&Bb, bbMap);
                prettyOutputStream << "Basic Block: " << bbName << endl;

                json bblockJson = json::object();
                bblockJson["name"] = bbName;

                json predJson = json::array();
                prettyOutputStream << "-Predecessors: ";
                for (BasicBlock *predBb : predecessors(&Bb)) {
                    std::string predName = getSlotAndName(predBb, bbMap);
                    predJson.push_back(predName);
                    prettyOutputStream << predName <<", ";
                }
                bblockJson["predecessors"] = predJson;
                prettyOutputStream << endl;

                json succJson = json::array();
                prettyOutputStream << "-Successors: ";
                for (BasicBlock *succBb : successors(&Bb)) {
                    std::string succName = getSlotAndName(succBb, bbMap);
                    succJson.push_back(succName);
                    prettyOutputStream << succName << ", ";
                }
                bblockJson["successors"] = succJson;
                prettyOutputStream << endl; 

                /*
                 * INSTRUCTIONS
                 */
                json instructionsJson = json::array();
                for (auto &Inst : Bb.getInstList()) {
                    json instructionJson = json::object();

                    unsigned numop = Inst.getNumOperands();
                    std::string opName = Inst.getOpcodeName(); // name of operation e.g. add, br, mul.
                    std::string defName = getSlotAndName(&Inst, regMap); // id of variable defined by this instr.
                    instructionJson["opname"] = opName;
                    instructionJson["def"] = defName;

                    prettyOutputStream << "   Instruction " << opName << " ops:" << numop << endl;
                    prettyOutputStream << "       DEF: "<< defName << endl;

                    /*
                     * OPERANDS
                     */
                    prettyOutputStream << "       USE: ";
                    json usesJson = json::array();
                    if (const PHINode *PN = dyn_cast<PHINode>(&Inst)) {
                        for (unsigned op = 0, Eop = PN->getNumIncomingValues(); op < Eop; ++op) {
                            json phiOpJson = json::object();

                            Value* v = PN->getIncomingValue(op);
                            BasicBlock* b = PN->getIncomingBlock(op);
                            std::string vName = getSlotAndName(v, regMap);
                            std::string bName = getSlotAndName(b, bbMap);
                            phiOpJson["val"] = vName;
                            phiOpJson["bb"] = bName;

                            usesJson.push_back(phiOpJson);
                            prettyOutputStream << "[" << bName << " -> " << vName << "], ";
                        }

                    } else {

                        for (unsigned i = 0; i < numop; i++) {
                            Value* op = Inst.getOperand(i);
                            std::string operandName = getSlotAndName(op, regMap);
                            usesJson.push_back(operandName);
                            prettyOutputStream << operandName <<", ";
                        }

                    }

                    instructionJson["use"] = usesJson;
                    instructionsJson.push_back(instructionJson);
                    prettyOutputStream << endl;
                }

                bblockJson["instructions"] = instructionsJson;
                bblocksJson.push_back(bblockJson);
                prettyOutputStream << endl;
            }
            
            functionJson["bblocks"] = bblocksJson;
            functionsJson.push_back(functionJson);

            return false;
        }

        bool doFinalization(Module &M) override {
            if (PrintOut) {
                cout << prettyOutputStream.str();
            }
            if (!ToJson.empty()) {
                jsonOutputStream << std::setw(4) << functionsJson; 
            }

            return false;
        }

    }; // end of struct ControlFlowExtractor


} // end of namespace

char ControlFlowExtractor::ID = 0;
static RegisterPass<ControlFlowExtractor> X("extract_cf", "Control Flow Extractor", false, false);
