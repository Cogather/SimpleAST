// UTF-8编码的中文测试文件
// 测试中文注释和标识符

#include <iostream>
#include <string>

// 用户信息结构体
struct UserInfo {
    std::string name;    // 用户姓名
    int age;            // 年龄
    std::string address; // 地址
};

/**
 * 初始化函数
 * 用于初始化系统配置
 * @return 返回是否成功
 */
bool Initialize() {
    // 这里是初始化逻辑
    std::cout << "系统初始化中..." << std::endl;
    return true;
}

/**
 * 获取用户信息
 * @param userId 用户ID
 * @return 用户信息对象
 */
UserInfo GetUserInfo(int userId) {
    UserInfo info;
    info.name = "张三";  // 默认用户名
    info.age = 25;      // 默认年龄
    info.address = "北京市海淀区"; // 默认地址
    return info;
}

/**
 * 主函数
 * 程序入口点
 */
int main() {
    // 初始化系统
    if (!Initialize()) {
        std::cerr << "初始化失败" << std::endl;
        return -1;
    }

    // 获取用户信息
    UserInfo user = GetUserInfo(1001);

    // 打印用户信息
    std::cout << "用户姓名: " << user.name << std::endl;
    std::cout << "用户年龄: " << user.age << std::endl;
    std::cout << "用户地址: " << user.address << std::endl;

    return 0;
}
