// 测试内部数据结构输出
#include <string>
#include <vector>

// 内部数据结构1
struct Point {
    int x;
    int y;
};

// 内部数据结构2
struct Rectangle {
    Point topLeft;
    Point bottomRight;
    int color;
};

// 辅助函数，使用内部数据结构
Point createPoint(int x, int y) {
    Point p;
    p.x = x;
    p.y = y;
    return p;
}

// 主函数，使用内部数据结构
Rectangle createRectangle(int x1, int y1, int x2, int y2, int c) {
    Rectangle rect;
    rect.topLeft = createPoint(x1, y1);       // 调用内部函数
    rect.bottomRight = createPoint(x2, y2);    // 调用内部函数
    rect.color = c;
    return rect;
}

// 计算矩形面积
int calculateArea(const Rectangle& rect) {
    int width = rect.bottomRight.x - rect.topLeft.x;
    int height = rect.bottomRight.y - rect.topLeft.y;
    return width * height;
}
