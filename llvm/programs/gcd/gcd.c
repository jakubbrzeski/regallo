#include <stdio.h>

int gcd(int a, int b) {
    if (a > b) {
        a = a ^ b;
        b = b ^ a;
        a = a ^ b;
    }

    while (b>0) {
        int tmp = b;
        b = a%b;
        a = tmp;
    }

    return a;
}

int main() {

    while (1) {
        int a, b;
        scanf("%d%d", &a, &b);
        printf("gcd = %d\n", gcd(a,b));

    }
    return 0;
}
