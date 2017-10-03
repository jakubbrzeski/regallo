# Python framework for testing register allocation algorithms

Regallo is a framework for testing and comparison of register allocation algorithms.
It consists of two parts:
* LLVM dynamic library for extracting Control Flow Graphs (CFG) of programs in .LL (LLVM assembly language) 
* Python library for testing allocation algorithms on the extracted CFGs.


## Extracting CFG from .LL files

     
### Requirements:
* LLVM source code
* Clang (binary or compiled from source together with LLVM)

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

     make -j($NUM_THREADS)
     
or if using another build tool:

     cmake --build .

Dynamic library for cfg extraction will be in:
     
     llvm/build/lib/LLVMCFGextractor.dylib

or if we use Linux:

     llvm/build/lib/LLVMCFGextractor.so
     
*opt* tool (see https://llvm.org/docs/CommandGuide/opt.html) that we also need, should be located in:

     llvm/build/lib/opt

### Compiling C and C++ programs into .LL ###
To compile C files we need to run

     clang -S -emit-llvm file.c
     
For C++, we use *clang++*.

     clang++ -S -emit-llvm file.cpp
     
In case of problems with compiling C++ it's worth to look at https://clang.llvm.org/get_started.html. 

### Extracting CFG from .LL into JSON.
It is necessary to use *opt* binary from the same LLVM version as the *LLVMCFGextractor* was compiled with.

Extract CFG into JSON (Mac OS and Linux respectively)

    opt -mem2reg -load=path/to/LLVMCFGextractor.dylib -extract_cfg file.ll -to-json file.json
    
    opt -mem2reg -load=path/to/LLVMCFGextractor.so -extract_cfg file.ll -to-json file.json

### CFG visualization
For each function in .LL file, generate .dot.cfg file

    opt -mem2reg -dot-cfg file.ll     

Generates PNG image with visualized CFG of the function

    dot -Tpng file.dot -o file.png

## Using py-regallo

### Requirements:
* Python 2.7
* pip (https://pypi.python.org/pypi/pip)

Install all required python libraries (in py-regallo directory)

    pip install -r requirements.txt

For interactive use and tutorial reading, *ipython* is necessary

    pip install ipython

Open tutorial

    ipython notebook py-regallo/tutorial.ipynb 

## Docker
It is possible to launch the pre-installed project in Docker, using the enclosed Dockerfile.
To build the image, run the command below in the main regallo directory:

     docker build -t image_name .
     
To run a container:

     docker run --net=host container_id
     
