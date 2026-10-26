#include "widget.hpp"

Widget* make_widget(const Config& cfg) {
    Widget* w = new Widget(cfg);
    return w;
}
