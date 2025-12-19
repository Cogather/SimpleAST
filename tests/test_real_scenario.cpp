// 模拟PidDiamMsgProc真实场景
#include <stddef.h>

// 基础类型定义
typedef unsigned int VOS_UINT32;
typedef void VOS_VOID;

// 进程ID常量
#define PID_DIAM 306
#define DOPRA_PID_TIMER 100
#define PID_SF 206
#define PID_DSP 242
#define PID_HAPD 204
#define PID_MAINTAIN 181
#define PID_OM 241

// 命令标志
#define DIAM_CMDFLAG_REQUEST 0x01
#define DIAM_CMDFLAG_ANSWER 0x00
#define DIAM_REQUEST_FLAG 0x01

// 返回码
#define DIAM_SUCCESS 0
#define VOS_OK 0

// 消息类型
#define SLF_HSF_RSP 100

// 宏定义
#define GET_DOPRA_MSG_LEN(msgPtr) ((msgPtr)->ulLength)
#define OFFSET_AFTER(type, member) (offsetof(type, member) + sizeof(((type*)0)->member))
#define OFFSET_OF(type, member) offsetof(type, member)
#define MSGLEN_CHECK_RETURN(cond) if (cond) return

// 数据结构
struct MsgBlock {
    VOS_UINT32 ulSenderPid;
    VOS_UINT32 ulReceiverPid;
    VOS_UINT32 ulLength;
};

struct tFeAppMsg {
    VOS_UINT32 ulSenderPid;
    VOS_UINT32 MsgType;
};

struct DiamAppMsg {
    VOS_UINT32 ulSenderPid;
    unsigned char CmdFlag;
    VOS_UINT32 EndId;
    VOS_UINT32 AppSubCbNo;
};

// 函数实现
VOS_VOID PidDiamMsgProc(MsgBlock *pMsg) {
    tFeAppMsg *pFeMsg = (tFeAppMsg *)pMsg;
    DiamAppMsg *pAppMsg = (DiamAppMsg *)pMsg;
    
    VOS_UINT32 ulRet = 0;
    VOS_UINT32 msg_len = 0;
    
    if (!CheckPidDiamMsg(pMsg)) {
        return;
    }
    
    msg_len = GET_DOPRA_MSG_LEN(pMsg);
    
    switch (pMsg->ulSenderPid) {
        case PID_DIAM:
            procMsgFromDiam(*pAppMsg);
            break;
            
        case DOPRA_PID_TIMER:
            AdaptDiamProcessMsgFromTimer(pMsg);
            break;
            
        case PID_SF:
            MSGLEN_CHECK_RETURN(msg_len < OFFSET_AFTER(tFeAppMsg, MsgType));
            if (SLF_HSF_RSP == pFeMsg->MsgType) {
                return;
            }
            break;
            
        case PID_DSP:
        case PID_HAPD:
            MSGLEN_CHECK_RETURN(msg_len < OFFSET_OF(DiamAppMsg, EndId));
            if (DIAM_CMDFLAG_ANSWER == (pAppMsg->CmdFlag & DIAM_REQUEST_FLAG)) {
                StatDiamTooBusy(pAppMsg);
            }
            if (DIAM_CMDFLAG_REQUEST == (pAppMsg->CmdFlag & DIAM_REQUEST_FLAG)) {
                pAppMsg->EndId = DspCreateEndId();
            }
            addOriginHostIntoDMLE(pAppMsg);
            ulRet = DiamProcAppMsg(pAppMsg);
            if (DIAM_SUCCESS != ulRet) {
                // Error
            }
            rmvOriginHostFromDMLE(pAppMsg->AppSubCbNo & 0xFFFF);
            break;
            
        case PID_MAINTAIN:
            break;
            
        case PID_OM:
            if (DiamMsgProcForPidOM(pMsg, pFeMsg) != VOS_OK) {
                return;
            }
            break;
            
        default:
            break;
    }
}
