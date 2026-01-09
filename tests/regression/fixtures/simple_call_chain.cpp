// 简单函数调用测试
#include <iostream>

int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}

int calculate(int x, int y) {
    int sum = add(x, y);
    int product = multiply(x, y);
    return sum + product;
}

int main() {
    int result = calculate(5, 3);
    std::cout << "Result: " << result << std::endl;
    return 0;
}
