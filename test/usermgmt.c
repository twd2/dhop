#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_USERS 100
#define MAX_LENGTH 65
#define MAX_LENGTH_STR "65"

struct user; typedef void (*print_func_t)(struct user *);
struct user {
    unsigned long age; char *name; void *data;
    print_func_t print;
};

void print_teacher(struct user *u) {
    printf("Teacher: %s, %lu years old, salary: %f RMB\n",
           u->name, u->age, *(double *)u->data);
}

void print_student(struct user *u) {
    printf("Student: %s, %lu years old, rank: %lu/150\n",
           u->name, u->age, *(unsigned long *)u->data);
}

struct user *users[MAX_USERS] = { NULL };

int alloc_slot() {
    for (int i = 0; i < MAX_USERS; ++i)
        if (!users[i]) return i;
    printf("No more slot!\n"); return -1;
}

int get_id() {
    printf("ID? "); int i = -1; scanf("%d", &i);
    if (!(0 <= i && i < MAX_USERS)) {
        printf("ID is out of bound!\n"); return -1;
    }
    return i;
}

struct user *get_user() {
    int i = get_id(); if (i < 0) return NULL;
    struct user *u = users[i];
    if (!u) { printf("No such user.\n"); return NULL; }
    return u;
}

void add_teacher() {
    int id = alloc_slot(); if (id < 0) return;
    struct user *u = users[id] = malloc(sizeof(struct user));
    printf("Name? ");
    char buf[MAX_LENGTH + 1];
    fgets(buf, sizeof(buf), stdin); // ignore remaining \n
    fgets(buf, sizeof(buf), stdin);
    buf[strlen(buf) - 1] = '\0'; // remove \n
    u->name = malloc(strlen(buf) + 1);
    strcpy(u->name, buf);
    printf("Age? "); scanf("%lu", &u->age);
    u->data = malloc(sizeof(double));
    printf("Salary? "); scanf("%lf", (double *)u->data);
    u->print = print_teacher;
    printf("New ID: %d\n", id);
}

void add_student() {
    int id = alloc_slot(); if (id < 0) return;
    struct user *u = users[id] = malloc(sizeof(struct user));
    printf("Name? ");
    char buf[MAX_LENGTH + 1];
    fgets(buf, sizeof(buf), stdin); // ignore remaining \n
    fgets(buf, sizeof(buf), stdin);
    buf[strlen(buf) - 1] = '\0'; // remove \n
    u->name = malloc(strlen(buf) + 1);
    strcpy(u->name, buf);
    printf("Age? "); scanf("%lu", &u->age);
    u->data = malloc(sizeof(unsigned long));
    printf("Rank? "); scanf("%lu", (unsigned long *)u->data);
    u->print = print_student;
    printf("New ID: %d\n", id);
}

void delete_user() {
    int i = get_id(); if (i < 0) return;
    struct user *u = users[i];
    if (!u) { printf("No such user.\n"); return; }
    free(u->name);
    if (u->data) free(u->data);
    free(u);
    users[i] = NULL;
}

void do_vulnerable() {
    struct user *u = get_user(); if (!u) return;
    printf("New name? ");
    char buf[MAX_LENGTH + 1];
    fgets(buf, sizeof(buf), stdin); // ignore remaining \n
    fgets(buf, sizeof(buf), stdin);
    buf[strlen(buf) - 1] = '\0'; // remove \n
    strcpy(u->name, buf);
}

void show_user() {
    struct user *u = get_user(); if (!u) return;
    u->print(u);
}

void show_menu() {
    printf("Welcome to User Management System.\n"
           "This is what you may need: %p.\n"
           "1. add an user (teacher)\n"
           "2. add an user (student)\n"
           "3. delete an user\n"
           "4. rename an user\n"
           "5. show an user\n"
           "6. exit\n", system);
}

int main() {
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    while (1) {
        show_menu(); printf("> ");
        int c; if (!scanf("%d", &c)) return 1;
        switch (c) {
            case 1: add_teacher(); break;
            case 2: add_student(); break;
            case 3: delete_user(); break;
            case 4: do_vulnerable(); break;
            case 5: show_user(); break;
            case 6: return 0; break;
            default: printf("???\n"); break;
        }
        printf("\n");
    };
    return 0;
}