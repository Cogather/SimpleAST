// 这是GBK编码的测试文件
// 文件描述：用于测试中文字符处理

#include <iostream>
#include <string>

/**
 * 用户信息结构体
 * 包含姓名、年龄、地址等基本信息
 */
struct UserInfo {
    std::string name;    // 用户的姓名
    int age;            // 用户的年龄
    std::string address; // 家庭住址
};

/**
 * 初始化系统配置
 * 返回值：初始化是否成功
 */
bool InitSystem() {
    std::cout << "系统正在初始化..." << std::endl;
    std::cout << "加载配置文件中..." << std::endl;
    return true;
}

/**
 * 获取用户详细信息
 * 参数：用户ID
 * 返回：用户信息结构体
 */
UserInfo GetUserInfo(int userId) {
    UserInfo info;
    info.name = "张三";
    info.age = 25;
    info.address = "北京市海淀区中关村大街1号";

    std::cout << "查询用户：" << userId << std::endl;
    return info;
}

/**
 * 打印用户信息
 */
void PrintUserInfo(const UserInfo& user) {
    std::cout << "姓名：" << user.name << std::endl;
    std::cout << "年龄：" << user.age << std::endl;
    std::cout << "地址：" << user.address << std::endl;
}

/**
 * 主函数
 */
int main() {
    // 步骤1：初始化
    if (!InitSystem()) {
        std::cerr << "初始化失败！程序退出" << std::endl;
        return -1;
    }

    // 步骤2：获取用户信息
    UserInfo user = GetUserInfo(1001);

    // 步骤3：显示信息
    std::cout << "\n=== 用户详细信息 ===" << std::endl;
    PrintUserInfo(user);

    return 0;
}
