// Test recursive structure with 3 levels
int funcC() {
    return 42;
}

int funcB() {
    return funcC() + 1;
}

int funcA() {
    return funcB() * 2;
}

int main() {
    return funcA();
}
