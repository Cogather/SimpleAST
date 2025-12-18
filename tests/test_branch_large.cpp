// 测试分支分析 - 包含复杂分支的大型文件
#include <string>

// 复杂函数1：消息处理（多个switch case + if分支）
int ProcessUserMessage(int msgType, int userId, const char* data, int dataLen) {
    // 参数验证
    if (userId <= 0) {
        return -1;
    }

    if (data == nullptr || dataLen <= 0) {
        return -2;
    }

    // 消息类型处理
    switch (msgType) {
        case 1:  // 登录消息
            if (dataLen < 100) {
                return -3;
            }
            return 0;

        case 2:  // 心跳消息
            return 0;

        case 3:  // 数据消息
            if (dataLen > 10000) {
                return -4;
            }
            for (int i = 0; i < dataLen && i < 1000; i++) {
                if (data[i] == 0) {
                    break;
                }
            }
            return 0;

        case 4:  // 登出消息
            return 0;

        case 5:  // 重连消息
            return 0;

        case 6:  // 更新消息
            return 0;

        case 7:  // 查询消息
            return 0;

        default:
            return -5;
    }
}

// 复杂函数2：数据验证（多层嵌套if + 循环）
bool ValidateDataPacket(const char* packet, int len, bool strictMode) {
    if (packet == nullptr || len <= 0) {
        return false;
    }

    if (packet[0] != 0xFF || packet[1] != 0xAA) {
        return false;
    }

    if (strictMode) {
        int checksum = 0;
        for (int i = 2; i < len - 1; i++) {
            checksum += packet[i];
        }

        if ((checksum & 0xFF) != packet[len - 1]) {
            return false;
        }

        int declaredLen = (packet[2] << 8) | packet[3];
        if (declaredLen != len - 4) {
            return false;
        }
    }

    return true;
}


int simpleFunc0(int x) {
    return x + 0;
}

int simpleFunc1(int x) {
    return x + 1;
}

int simpleFunc2(int x) {
    return x + 2;
}

int simpleFunc3(int x) {
    return x + 3;
}

int simpleFunc4(int x) {
    return x + 4;
}

int simpleFunc5(int x) {
    return x + 5;
}

int simpleFunc6(int x) {
    return x + 6;
}

int simpleFunc7(int x) {
    return x + 7;
}

int simpleFunc8(int x) {
    return x + 8;
}

int simpleFunc9(int x) {
    return x + 9;
}

int simpleFunc10(int x) {
    return x + 10;
}

int simpleFunc11(int x) {
    return x + 11;
}

int simpleFunc12(int x) {
    return x + 12;
}

int simpleFunc13(int x) {
    return x + 13;
}

int simpleFunc14(int x) {
    return x + 14;
}

int simpleFunc15(int x) {
    return x + 15;
}

int simpleFunc16(int x) {
    return x + 16;
}

int simpleFunc17(int x) {
    return x + 17;
}

int simpleFunc18(int x) {
    return x + 18;
}

int simpleFunc19(int x) {
    return x + 19;
}

int simpleFunc20(int x) {
    return x + 20;
}

int simpleFunc21(int x) {
    return x + 21;
}

int simpleFunc22(int x) {
    return x + 22;
}

int simpleFunc23(int x) {
    return x + 23;
}

int simpleFunc24(int x) {
    return x + 24;
}

int simpleFunc25(int x) {
    return x + 25;
}

int simpleFunc26(int x) {
    return x + 26;
}

int simpleFunc27(int x) {
    return x + 27;
}

int simpleFunc28(int x) {
    return x + 28;
}

int simpleFunc29(int x) {
    return x + 29;
}

int simpleFunc30(int x) {
    return x + 30;
}

int simpleFunc31(int x) {
    return x + 31;
}

int simpleFunc32(int x) {
    return x + 32;
}

int simpleFunc33(int x) {
    return x + 33;
}

int simpleFunc34(int x) {
    return x + 34;
}

int simpleFunc35(int x) {
    return x + 35;
}

int simpleFunc36(int x) {
    return x + 36;
}

int simpleFunc37(int x) {
    return x + 37;
}

int simpleFunc38(int x) {
    return x + 38;
}

int simpleFunc39(int x) {
    return x + 39;
}

int simpleFunc40(int x) {
    return x + 40;
}

int simpleFunc41(int x) {
    return x + 41;
}

int simpleFunc42(int x) {
    return x + 42;
}

int simpleFunc43(int x) {
    return x + 43;
}

int simpleFunc44(int x) {
    return x + 44;
}

int simpleFunc45(int x) {
    return x + 45;
}

int simpleFunc46(int x) {
    return x + 46;
}

int simpleFunc47(int x) {
    return x + 47;
}

int simpleFunc48(int x) {
    return x + 48;
}

int simpleFunc49(int x) {
    return x + 49;
}
