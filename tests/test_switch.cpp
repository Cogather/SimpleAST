// 测试switch分支识别
#include <string>

enum MessageType {
    MSG_LOGIN = 1,
    MSG_LOGOUT = 2,
    MSG_DATA = 3,
    MSG_HEARTBEAT = 4
};

int HandleMessage(MessageType msgType, const char* data) {
    switch (msgType) {
        case MSG_LOGIN:
            return 100;
        
        case MSG_LOGOUT:
            return 200;
        
        case MSG_DATA:
            if (data == nullptr) {
                return -1;
            }
            return 300;
        
        case MSG_HEARTBEAT:
            return 400;
        
        default:
            return -999;
    }
}

int ProcessCommand(int cmd) {
    switch (cmd) {
        case 0:
        case 1:
            return 10;
        case 2:
            return 20;
        case 3:
            return 30;
    }
    return -1;  // 无default但有返回
}
