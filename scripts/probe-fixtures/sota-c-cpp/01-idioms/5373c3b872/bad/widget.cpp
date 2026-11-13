#include "widget.h"

Widget::Widget(int n) : n_(n) {
    init();
}

Widget::~Widget() {
    shutdown();
}
