#!/bin/bash

while [[ $# -gt 1 ]]
do
key="$1"

case $key in
    -in|--input_path)
    INPUT_PATH="$2"
    shift 
    ;;
    -out|--output_path)
    OUTPUT_PATH="$2"
    shift 
    ;;
    -llvm|--llvm_path)
    LLVM_PATH="$2"
    shift 
    ;;
    *)
    # unknown option
    ;;
esac
shift 
done

HELP='
    FLAGS:\n
    -in\t     path to directory with .C files\n
    -out\t    path to the output directory where .ll and .json files will be located.\n
    -llvm\t   path to LLVM build directory (assuming llvm/bin contains clang and opt AND llvm/lib contains CFGextractor dynamic library)\n
    '

if [ -z $INPUT_PATH ]; then 
    echo -e $HELP
    echo "You didn't pass the input path (-in)";
    exit 1
fi

if [ -z $OUTPUT_PATH ]; then 
    echo -e $HELP
    echo "You didn't pass the output path (-out)";
    exit 1
fi

if [ -z $LLVM_PATH ]; then 
    echo -e $HELP
    echo "You didn't pass the llvm build path (-llvm)";
    exit 1
fi

for f in $(find $INPUT_PATH -name '*.c')
do
    basename=$(basename $f .c)
    echo `$LLVM_PATH/bin/clang -S -emit-llvm $f -o $OUTPUT_PATH/$basename.ll`
    # FOR LINUX CHANGE .dylib FOR .so
    echo `$LLVM_PATH/bin/opt -mem2reg -load $LLVM_PATH/lib/LLVMCFGextractor.dylib -extract_cfg $OUTPUT_PATH/$basename.ll -to-json $OUTPUT_PATH/$basename.json >/dev/null` 
    echo "saving \"$OUTPUT_PATH$basename.json\""
done

