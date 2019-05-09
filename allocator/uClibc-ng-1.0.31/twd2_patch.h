#ifndef attribute_hidden
# define attribute_hidden __attribute__ ((visibility ("hidden")))
#endif
#ifndef __attribute_aligned__
# define __attribute_aligned__(size) __attribute__ ((__aligned__ (size)))
#endif
#ifndef likely
# define likely(x)        __builtin_expect((!!(x)),1)
#endif
#ifndef unlikely
# define unlikely(x)   __builtin_expect((!!(x)),0)
#endif
#ifndef __set_errno
#define __set_errno(val) (errno = (val))
#endif
#ifndef libc_hidden_proto
#define libc_hidden_proto(x)
#endif
#ifndef weak_alias
#  define weak_alias(name, aliasname) _weak_alias (name, aliasname)
#  define _weak_alias(name, aliasname) \
  extern __typeof (name) aliasname __attribute__ ((weak, alias (#name)));
#endif
#ifndef libc_hidden_def
#define libc_hidden_def(x)
#endif
