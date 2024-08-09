#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <algorithm>
#include <limits>
#include <random>

using namespace std;
random_device rd;
mt19937 gen(rd());

int randint(int low, int high)
{
    uniform_int_distribution<> dist(low, high);
    return dist(gen);
}

double qubo_energy(const vector<vector<int>>& bits, const vector<vector<double>>& Q) {
    int L = bits.size();
    int N = bits[0].size();
    double energy = 0.0;

    for (int i = 0; i < L; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int k = 0; k < N; ++k) {
                energy += Q[j][k] * bits[i][j] * bits[i][k];
            }
        }
    }

    return energy;
}

void monte_carlo_step(vector<vector<int>>& bits, const vector<vector<double>>& Q, double T, double max_dE = 1000.0) {
    int L = bits.size();
    int N = bits[0].size();

    for (int i = 0; i < L * N; ++i) {
        int layer = randint(1,L);
        int bit = randint(1,N);
        int current_bit = bits[layer][bit];
        bits[layer][bit] = 1 - bits[layer][bit];

        double dE = (1 - 2 * current_bit) * (inner_product(Q[bit].begin(), Q[bit].end(), bits[layer].begin(), 0.0) - Q[bit][bit]);
        dE = max(-max_dE, min(dE, max_dE));

        if (static_cast<double>(rand()) / RAND_MAX >= exp(-dE / T)) {
            bits[layer][bit] = current_bit;
        }
    }
}

pair<vector<int>, double> quantum_annealing(int L, int N, const vector<vector<double>>& Q, double T, int mc_steps, int anneal_steps) {
    vector<vector<int>> bits(L, vector<int>(N));

    for (int i = 0; i < L; ++i) {
        for (int j = 0; j < N; ++j) {
            bits[i][j] = randint(0,1);
        }
    }

    for (int i = 0; i < anneal_steps; ++i) {
        for (int j = 0; j < mc_steps; ++j) {
            monte_carlo_step(bits, Q, T);
        }
        T *= 0.95;
    }

    double min_energy = numeric_limits<double>::infinity();
    vector<int> best_bits;

    for (int layer = 0; layer < L; ++layer) {
        double layer_energy = qubo_energy({bits[layer]}, Q);
        if (layer_energy < min_energy) {
            min_energy = layer_energy;
            best_bits = bits[layer];
        }
    }

    min_energy = qubo_energy({best_bits}, Q);
    return {best_bits, min_energy};
}

int main() {
    int mc_steps = 100;  // Number of Monte Carlo steps
    int anneal_steps = 100;  // Number of annealing steps
    int L = 3;  // Number of layers
    int N = 10; // Number of bits in each layer
    double T = 1.0;
    vector<vector<double>> Q(N, vector<double>(N, 0.0));

    for (int i = 0; i < N; ++i) {
        Q[i][i] = -1.0;
    }

    for (int j = 0; j < N; ++j) {
        for (int i = j; i < N; ++i) {
            if (i != j) {
                Q[i][j] = 2.0;
            }
        }
    }
    cout << "Hello World" << endl;
    pair<vector<int>, double> result = quantum_annealing(L, N, Q, T, mc_steps, anneal_steps);

    cout << "Best bits: ";
    for (int bit : result.first) {
        cout << bit << " ";
    }
    cout << endl;

    cout << "Minimum energy: " << result.second << endl;

    return 0;
}


