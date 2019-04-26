#include <iostream>
#include <string>

#include <llvm/IR/CFG.h>
#include <llvm/IR/InstVisitor.h>
#include <llvm/IR/Dominators.h>
#include <llvm/IRReader/IRReader.h>
#include <llvm/Support/SourceMgr.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/Analysis/LoopInfo.h>


using namespace llvm;

std::string get_name(const Value &node)
{
  if (!node.getName().empty())
  {
    return node.getName().str();
  }

  std::string str;
  raw_string_ostream os(str);

  node.printAsOperand(os, false);
  return os.str();
}

uint64_t get_address(const std::string &name)
{
  size_t pos = name.find_last_of('_');
  if (pos == std::string::npos || pos == name.length() - 1)
  {
    return -1;
  }
  try
  {
    return std::stoi(name.substr(pos + 1), nullptr, 16);
  }
  catch (std::invalid_argument)
  {
    return -1;
  }
}

uint64_t get_entry_address(Function &func)
{
  const BasicBlock &entry_bb = func.getEntryBlock();
  return get_address(get_name(entry_bb));
}

Function *find_entry_point(Module &mod)
{
  for (auto &func : mod)
  {
    if (func.getName() == "entry_point" || func.getName() == "_start")
    {
      return &func;
    }
  }
  return nullptr;
}

Function *find_main(Module &mod)
{
  // Find function named main.
  for (auto &func : mod)
  {
    if (func.getName() == "main" || func.getName() == "_main")
    {
      return &func;
    }
  }
  // Find a __libc_start_main call in the entry function like this:
  // > call i32 @__libc_start_main(i64 1520, ...)
  Function *entry_func = find_entry_point(mod);
  if (!entry_func)
  {
    std::cout << "The entry point is not found." << std::endl;
    return nullptr;
  }
  std::cout << std::hex << "The entry point is at 0x"
            << get_entry_address(*entry_func) << std::endl;
  uint64_t main_addr = -1;
  bool found = false;
  for (auto &bb : *entry_func)
  {
    for (auto &inst : bb)
    {
      if (CallInst *call_inst = dyn_cast<CallInst>(&inst))
      {
        std::string callee_name = get_name(*call_inst->getCalledFunction());
        // Find __libc_start_main call.
        if (callee_name.find("start") != std::string::npos &&
            callee_name.find("main") != std::string::npos)
        {
          if (ConstantInt *const_int = dyn_cast<ConstantInt>(call_inst->getArgOperand(0)))
          {
            main_addr = const_int->getLimitedValue();
            found = true;
            break;
          }
        }
      }
    }
    if (found)
    {
      break;
    }
  }
  for (auto &func : mod)
  {
    if (get_entry_address(func) == main_addr)
    {
      return &func;
    }
  }
  return nullptr;
}

void find_main_loop(Module &mod)
{
  Function *main_func = find_main(mod);
  if (!main_func)
  {
    std::cout << "The main function is not found." << std::endl;
    return;
  }
  std::cout << std::hex << "The main function is at 0x" << get_entry_address(*main_func) << std::endl;
  DominatorTree dt(*main_func);
  LoopInfoBase<BasicBlock, Loop> li;
  li.releaseMemory();
  li.analyze(dt);
  /*std::cout << "dominators:" << std::endl;
  for (auto &bb1 : *main_func)
  {
    std::cout << get_name(bb1) << "(" << li->isLoopHeader(&bb1) << "):" << std::endl;
    for (auto &bb2 : *main_func)
    {
      if (dt.dominates(&bb2, &bb1))
      {
        std::cout << "    " << get_name(bb2) << std::endl;
      }
    }
  }*/
  Loop *biggest_loop = nullptr;
  size_t max_blocks = 0;
  for (Loop *loop : li)
  {
    if (loop->getLoopDepth() > 1)
    {
      continue;
    }
    std::cout << "[DEBUG] Find a loop starting with " << get_name(*loop->getHeader()) << " having "
              << loop->getNumBlocks() << " blocks" << std::endl;
    if (loop->getNumBlocks() > max_blocks)
    {
      biggest_loop = loop;
      max_blocks = loop->getNumBlocks();
    }
  }
  /*std::string str;
  raw_string_ostream OS(str);
  dt.print(OS);
  li.print(OS);
  std::cout << OS.str() << std::endl;*/
  if (biggest_loop)
  {
    std::cout << "The entry basic block of the main loop should be at 0x"
              << std::hex << get_address(get_name(*biggest_loop->getHeader())) << std::endl;
  }
  else
  {
    std::cout << "The main loop is not found." << std::endl;
  }
}

int main(int argc, char const *argv[])
{
  if (argc < 2)
  {
    errs() << "Usage: " << argv[0] << " <LLVM IR file>\n";
    return 1;
  }

  LLVMContext llvmctx;

  // Parse the input LLVM IR file into a module.
  SMDiagnostic Err;
  auto module = parseIRFile(argv[1], Err, llvmctx);
  if (!module)
  {
    Err.print(argv[0], errs());
    return 1;
  }

  find_main_loop(*module);
  return 0;
}
