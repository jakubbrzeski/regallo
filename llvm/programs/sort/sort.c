void sort(int *tab, int n) {
    for (int i=1; i<n; i++) {
        int j = i-1;
        while(j>=0 && tab[j]>tab[j+1]) {
            int tmp = tab[j];
            tab[j] = tab[j+1];
            tab[j+1] = tmp;
            j--;
        }
    }
}

int main() {
    int n;
    scanf("%d", &n);
    int *tab = malloc(n*sizeof(int));
    for(int i=0; i<n; i++) {
        scanf("%d", &tab[i]);
    }

    sort(tab, n);
    for (int i=0; i<n; i++) printf("%d ", tab[i]);
    printf("\n");

    return 0;
}
