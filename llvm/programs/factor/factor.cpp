#include<iostream>
#include<cstring>
#include<cstdio>
#include<vector>

using namespace std;

const int mysize = 1000002;
char T[mysize];
int PS[mysize];

void compute_pref_suf(char *T, int *PS, int n) {
    int t = -1;
    PS[0] = -1;
    for(int i=1; i<=n; i++) {
        while(t>-1 && T[i]!=T[t+1]) t=PS[t];
        PS[i]=++t;
    }
    
    for(int i=1; i<=n; i++) {
        int t = PS[i];
        if (t > 0) {
            while(PS[t]>0) {
                t = PS[t]; 
            }
            PS[i] = t;
        }
    }
    for(int i=1; i<=n; i++) {
        if (PS[i] == 0) PS[i]=i;
    }
}

// From Text Algorithms p.379
vector<int> factor(char *T, int n) {
    int ms = 0, j = 1, k = 1, p = 1;
    T[n+1]='a'-1;
    vector<int> result;
    while (j+k <= n+1) {
        char aprim = T[ms+k];
        char a = T[j+k];
        if (aprim < a) {
            j = j+k;
            k = 1;
            p = j - ms;
        }
        else if (aprim == a) {
            if (k != p) {
                k++;
            } else {
                j+=p;
                k = 1;
            }
        } else {
            do {
                result.push_back(ms+1);
                ms += p;
            } while(ms < j);
            j = ms+1;
            k = 1;
            p = 1;
        }
    }
    return result;
}

int main() {
    int z;
    scanf("%d", &z);
    while(z--) {
        scanf("%s", T+1);
        int n = strlen(T+1)+1;
        vector<int> res = factor(T, n);
        res.push_back(n);
        for(int i=0; i<res.size()-1; i++) {
            compute_pref_suf(T+res[i]-1,PS+res[i]-1, res[i+1]-res[i]);
            for(int j=res[i]; j<res[i+1]; j++) {
                printf("%d ", j-PS[j]+1);
            }

        }
        printf("\n"); 
    }
    return 0;
}
