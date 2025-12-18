// 大型测试文件，包含内部数据结构
#include <string>

// 内部数据结构
struct Point {
    int x;
    int y;
};

struct Rectangle {
    Point topLeft;
    Point bottomRight;
};

// 使用内部数据结构的辅助函数
Point createPoint(int x, int y) {
    Point p;
    p.x = x;
    p.y = y;
    return p;
}

// 主函数，使用内部数据结构
Rectangle createRectangle(int x1, int y1, int x2, int y2) {
    Rectangle rect;
    rect.topLeft = createPoint(x1, y1);
    rect.bottomRight = createPoint(x2, y2);
    return rect;
}

int getRectWidth(const Rectangle& rect) {
    return rect.bottomRight.x - rect.topLeft.x;
}

int getRectHeight(const Rectangle& rect) {
    return rect.bottomRight.y - rect.topLeft.y;
}


int dummyFunc0() {
    return 0;
}

int dummyFunc1() {
    return 1;
}

int dummyFunc2() {
    return 2;
}

int dummyFunc3() {
    return 3;
}

int dummyFunc4() {
    return 4;
}

int dummyFunc5() {
    return 5;
}

int dummyFunc6() {
    return 6;
}

int dummyFunc7() {
    return 7;
}

int dummyFunc8() {
    return 8;
}

int dummyFunc9() {
    return 9;
}

int dummyFunc10() {
    return 10;
}

int dummyFunc11() {
    return 11;
}

int dummyFunc12() {
    return 12;
}

int dummyFunc13() {
    return 13;
}

int dummyFunc14() {
    return 14;
}

int dummyFunc15() {
    return 15;
}

int dummyFunc16() {
    return 16;
}

int dummyFunc17() {
    return 17;
}

int dummyFunc18() {
    return 18;
}

int dummyFunc19() {
    return 19;
}

int dummyFunc20() {
    return 20;
}

int dummyFunc21() {
    return 21;
}

int dummyFunc22() {
    return 22;
}

int dummyFunc23() {
    return 23;
}

int dummyFunc24() {
    return 24;
}

int dummyFunc25() {
    return 25;
}

int dummyFunc26() {
    return 26;
}

int dummyFunc27() {
    return 27;
}

int dummyFunc28() {
    return 28;
}

int dummyFunc29() {
    return 29;
}

int dummyFunc30() {
    return 30;
}

int dummyFunc31() {
    return 31;
}

int dummyFunc32() {
    return 32;
}

int dummyFunc33() {
    return 33;
}

int dummyFunc34() {
    return 34;
}

int dummyFunc35() {
    return 35;
}

int dummyFunc36() {
    return 36;
}

int dummyFunc37() {
    return 37;
}

int dummyFunc38() {
    return 38;
}

int dummyFunc39() {
    return 39;
}

int dummyFunc40() {
    return 40;
}

int dummyFunc41() {
    return 41;
}

int dummyFunc42() {
    return 42;
}

int dummyFunc43() {
    return 43;
}

int dummyFunc44() {
    return 44;
}

int dummyFunc45() {
    return 45;
}

int dummyFunc46() {
    return 46;
}

int dummyFunc47() {
    return 47;
}

int dummyFunc48() {
    return 48;
}

int dummyFunc49() {
    return 49;
}

int dummyFunc50() {
    return 50;
}

int dummyFunc51() {
    return 51;
}

int dummyFunc52() {
    return 52;
}

int dummyFunc53() {
    return 53;
}

int dummyFunc54() {
    return 54;
}

int dummyFunc55() {
    return 55;
}
