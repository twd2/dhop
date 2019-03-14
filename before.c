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
ptr7 = malloc(1760);
// 2 allocated chunks
free(ptr7);
// 1 allocated chunks
free(ptr6);
// 0 allocated chunks
ptr10 = malloc(14032);
// 1 allocated chunks
ptr11 = malloc(64);
// 2 allocated chunks
ptr12 = malloc(3808);
// 3 allocated chunks
free(ptr11);
// 2 allocated chunks
ptr14 = malloc(256);
// 3 allocated chunks
ptr15 = malloc(512);
// 4 allocated chunks
ptr16 = malloc(9824);
// 5 allocated chunks
free(ptr10);
// 4 allocated chunks
ptr18 = malloc(4096);
// 5 allocated chunks
ptr19 = malloc(512);
// 6 allocated chunks
