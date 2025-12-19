// 模拟真实场景：多个if + 一个大switch
void ComplexFunction(int msgType, void* data, int len) {
    // 前面有几个if条件
    if (!CheckValid(data)) {
        return;
    }
    
    if (len < 0) {
        return;
    }
    
    if (data == nullptr) {
        return;
    }
    
    // 中间可能还有逻辑
    int result = 0;
    
    // 然后是一个大的switch
    switch (msgType) {
        case 1:  // PID_DIAM
            ProcessDiam();
            break;
        
        case 2:  // DOPRA_PID_TIMER
            ProcessTimer();
            break;
        
        case 3:  // PID_SF
            if (CheckSLF()) {
                ProcessSLF();
            }
            break;
        
        case 4:  // PID_DSP
        case 5:  // PID_HAPD
            if (IsAnswer()) {
                StatTooBusy();
            }
            if (IsRequest()) {
                CreateEndId();
            }
            ProcessApp();
            break;
        
        case 6:  // PID_MAINTAIN
            break;
        
        case 7:  // PID_OM
            ProcessOM();
            break;
        
        default:
            LogError();
            break;
    }
    
    // 后面可能还有if
    if (result != 0) {
        HandleError();
    }
}
