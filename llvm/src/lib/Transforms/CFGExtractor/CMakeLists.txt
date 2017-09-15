add_llvm_loadable_module( LLVMCFGextractor
  cfgextractor.cpp

  PLUGIN_TOOL
  opt

  DEPENDS
  intrinsics_gen
  )
