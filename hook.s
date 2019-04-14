.macro STORE_CTX
  sub $128, %rsp # red zone
  pushfq
  push %rax
  push %rcx
  push %rdx
  push %rbx
  push %rbp
  push %rsi
  push %rdi
  push %r8
  push %r9
  push %r10
  push %r11
  push %r12
  push %r13
  push %r14
  push %r15
.endm

.macro LOAD_CTX
  pop %r15
  pop %r14
  pop %r13
  pop %r12
  pop %r11
  pop %r10
  pop %r9
  pop %r8
  pop %rdi
  pop %rsi
  pop %rbp
  pop %rbx
  pop %rdx
  pop %rcx
  pop %rax
  popfq
  add $128, %rsp
.endm

.section .text

.extern do_hook
.extern do_next_hook

.global asm_code
.hidden asm_code
.global asm_hook_entry
.hidden asm_hook_entry
.global asm_ctx
.hidden asm_ctx
.global asm_do_hook
.hidden asm_do_hook
.global asm_hook_ret
.hidden asm_hook_ret
.global asm_code_end
.hidden asm_code_end

asm_code:

asm_hook_entry:
STORE_CTX
# movq $ctx, %rdi
.byte 0x48, 0xbf
asm_ctx:
.quad 0
mov %rsp, %rsi
# movq $do_hook_func, %rax
.byte 0x48, 0xb8
asm_do_hook:
.quad 0
call *%rax
LOAD_CTX
# jmp to original inst
.byte 0xe9
asm_hook_ret:
.long -4

asm_code_end:
