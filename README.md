# Register Allocators testing framework

Regallo is a framework for testing and comparison of register allocators.
It consists of two parts:
* LLVM dynamic library for extracting Control Flow Graphs (CFG) of functions from programs in C.
* Python library for testing various register allocators on the extracted functions' CFGs.


## Extracting CFG from C files

     
### Requirements:
* LLVM source code
* Clang

It was tested with LLVM 5.0 and Clang 3.9.0. Other version should work but it is important
to use dynamic library with the same LLVM version it was compiled with.

LLVM and Clang source codes as well as binaries are available here: http://releases.llvm.org/download.html#5.0.0

### Installation
Let's assume we have cloned regallo repository, downloaded LLVM source code into the same directory and got the Clang binary. To build and use llvm with the CFGextractor library we should do the following:


Move llvm source files to regallo's llvm/src directory
     
     tar xf llvm-5.0.0.src.tar.xz -C regallo/llvm/src --strip-components 1

Add CFGextractor library directory to CMakeLists: 

     echo "add_subdirectory(CFGExtractor)" >> regallo/llvm/src/lib/Transforms/CMakeLists.txt

Create build directory

     mkdir regallo/llvm/build

In regallo/llvm/build run: 

     cmake ../src
     
It will generate files necessary for building LLVM.

At the same directory, build LLVM 

     make -j2
     
or if using another build tool:

     cmake --build .

Dynamic library for cfg extraction will be in:
     
     llvm/build/lib/LLVMCFGextractor.dylib

or if we use Linux:

     llvm/build/lib/LLVMCFGextractor.so
     
opt tool (see https://llvm.org/docs/CommandGuide/opt.html) that we also need should be in:

     llvm/build/lib/opt


### Extracting CFG from programs in C into JSON.
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

Install all required python libraries

    py-regallo/make

For interactive use and tutorial reading ipython is necessary

    pip install ipython

Show tutorial

    ipython notebook py-regallo/tutorial.ipynb 
