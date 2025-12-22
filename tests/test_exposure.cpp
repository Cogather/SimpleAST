// 测试函数暴露状态的实现文件
#include "test_exposure.h"
#include <iostream>

// API函数 - 在头文件中声明
int PublicFunction(int x, int y) {
    return x + y;
}

// API函数 - 在头文件中声明
void ProcessData(const char* data) {
    std::cout << "Processing: " << data << std::endl;
}

// INTERNAL函数 - static，不能被extern
static int InternalHelper(int x) {
    return x * 2;
}

// EXPORTED函数 - 没有在头文件中声明，但不是static，可以被extern使用
void UtilityFunction() {
    std::cout << "Utility function" << std::endl;
}

// 主函数，调用以上所有函数
int main() {
    int result = PublicFunction(10, 20);
    ProcessData("test data");
    int helper = InternalHelper(5);
    UtilityFunction();
    return 0;
}
