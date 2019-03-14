// 0 allocated chunks
ptr0 = malloc(1048576);
// 1 allocated chunks
free(ptr0);
// 0 allocated chunks
ptr2 = malloc(6640);
// 1 allocated chunks
free(ptr2);
// 0 allocated chunks
ptr4 = malloc(15392);
// 1 allocated chunks
free(ptr4);
// 0 allocated chunks
ptr6 = malloc(2992);
// 1 allocated chunks
ptr7 = malloc(4096);
// 2 allocated chunks
ptr8 = malloc(1760);
// 3 allocated chunks
free(ptr8);
// 2 allocated chunks
free(ptr6);
// 1 allocated chunks
ptr11 = malloc(14032);
// 2 allocated chunks
ptr12 = malloc(64);
// 3 allocated chunks
ptr13 = malloc(3808);
// 4 allocated chunks
free(ptr12);
// 3 allocated chunks
ptr15 = malloc(256);
// 4 allocated chunks
ptr16 = malloc(512);
// 5 allocated chunks
ptr17 = malloc(9824);
// 6 allocated chunks
free(ptr11);
// 5 allocated chunks
ptr19 = malloc(4096);
// 6 allocated chunks
ptr20 = malloc(512);
// 7 allocated chunks
