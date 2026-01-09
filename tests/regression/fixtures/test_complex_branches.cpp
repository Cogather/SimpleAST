// 测试分支分析 - 包含复杂分支的函数
#include <string>

// 处理用户消息 - 包含多个分支
int ProcessUserMessage(int msgType, int userId, const char* data, int dataLen) {
    // 参数验证
    if (userId <= 0) {
        return -1;  // 错误：无效用户ID
    }

    if (data == nullptr || dataLen <= 0) {
        return -2;  // 错误：无效数据
    }

    // 消息类型处理
    switch (msgType) {
        case 1:  // 登录消息
            if (dataLen < 100) {
                return -3;  // 数据长度不足
            }
            // 处理登录...
            return 0;

        case 2:  // 心跳消息
            return 0;  // 直接返回

        case 3:  // 数据消息
            if (dataLen > 10000) {
                return -4;  // 数据过大
            }
            // 处理数据...
            for (int i = 0; i < dataLen && i < 1000; i++) {
                if (data[i] == 0) {
                    break;  // 遇到结束符
                }
            }
            return 0;

        case 4:  // 登出消息
            return 0;

        default:
            return -5;  // 未知消息类型
    }
}

// 复杂的数据验证函数
bool ValidateDataPacket(const char* packet, int len, bool strictMode) {
    if (packet == nullptr || len <= 0) {
        return false;
    }

    // 检查包头
    if (packet[0] != 0xFF || packet[1] != 0xAA) {
        return false;
    }

    // 严格模式下的额外检查
    if (strictMode) {
        // 检查校验和
        int checksum = 0;
        for (int i = 2; i < len - 1; i++) {
            checksum += packet[i];
        }

        if ((checksum & 0xFF) != packet[len - 1]) {
            return false;  // 校验失败
        }

        // 检查长度字段
        int declaredLen = (packet[2] << 8) | packet[3];
        if (declaredLen != len - 4) {
            return false;  // 长度不匹配
        }
    }

    return true;
}

// 简单函数（用于对比）
int Add(int a, int b) {
    return a + b;
}
