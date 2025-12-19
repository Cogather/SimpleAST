// 模拟用户的真实场景
struct MsgBlock {
    unsigned int ulSenderPid;
};

struct tFeAppMsg {
    int MsgType;
};

struct DiamAppMsg {
    int CmdFlag;
};

void PidDiamMsgProc(MsgBlock *pMsg) {
    tFeAppMsg *pFeMsg = (tFeAppMsg *)pMsg;
    DiamAppMsg *pAppMsg = (DiamAppMsg *)pMsg;
    
    if (!CheckValid(pMsg)) {
        return;
    }
    
    switch (pMsg->ulSenderPid) {
        case 1:
            ProcessDiam();
            break;
        case 2:
            ProcessTimer();
            break;
        default:
            LogError();
            break;
    }
}
