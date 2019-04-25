#include <stdio.h>

void foo1(void);
void foo2(void);
void foo3(void);
void foo4(void);
void foo5(void);
void foo6(void);
void foo7(void);
void foo8(void);
void bar1(void);
void bar2(void);
void bar3(void);
void bar4(void);
void bar5(void);
void bar6(void);
void bar7(void);
void bar8(void);


int main(int argc, char **argv)
{
  setvbuf(stdin, NULL, _IONBF, 0);
  setvbuf(stdout, NULL, _IONBF, 0);
  setvbuf(stderr, NULL, _IONBF, 0);
  while (argc--)
  {
    switch (argv[argc][0])
    {
    case 1:
      foo1();
      break;
    case 2:
      foo2();
      break;
    case 3:
      foo3();
      break;
    case 4:
      foo4();
      break;
    case 5:
      foo5();
      break;
    case 6:
      foo6();
      break;
    case 7:
      foo7();
      break;
    case 8:
      foo8();
      break;
    default:
      return 1;
      break;
    }
    switch (argv[argc][1])
    {
    case 1:
      bar1();
      break;
    case 2:
      bar2();
      break;
    case 3:
      bar3();
      break;
    case 4:
      bar4();
      break;
    case 5:
      for (int i = 1; i < argv[argc][2]; ++i)
      {
        bar5();
      }
      break;
    case 6:
      bar6();
      break;
    case 7:
      bar7();
      break;
    case 8:
      bar8();
      break;
    default:
      return 1;
      break;
    }
    for (int i = 0; i < argv[argc][2]; ++i)
    {
      foo1();
    }
  }
  for (int i = 0; i < argv[argc][3]; ++i)
  {
    bar1();
  }
  return 0;
}
