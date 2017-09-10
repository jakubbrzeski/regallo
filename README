# Register Allocators testing framework

Regallo is a framework for testing and comparison of register allocators.
It consists of two parts:
* LLVM dynamic library for extracting Control Flow Graphs (CFG) of functions from programs in C.
* Python library for testing various register allocators on the extracted functions' CFGs.


## Extracting CFG from C files

     
### Requirements:
* LLVM 5.0 (with opt tool)
* Clang (older versions should work)

Dynamic library needed for control flow extraction was compiled using LLVM 5.0 and
this version is neccessary to run it. clang (older versions should work)
LINK: http://releases.llvm.org/download.html#5.0.0

### Extracting CFG from programs in C into JSON.
For each .c file:
Compile to .ll (LLVM IR)

    clang -S -emit-llvm file.c
        
Extract CFG into JSON

    opt -mem2reg -load=path/to/LLVMCFGextractor.dylib -extract_cfg file.ll -to-json file.json

### CFG visualization
For each function in .ll file generates .dot.cfg file

    opt -mem2reg -dot-cfg hello.ll     

Generates PNG with visualized CFG of the function

    dot -Tpng file.dot -o file.png

## Using py-regallo

### Install all required python libraries.
    py-regallo/make

### For interactive use and tutorial reading ipython is necessary.
    pip install ipython

### Tutorial.
    ipython notebook py-regallo/tutorial/tutorial.ipynb 
