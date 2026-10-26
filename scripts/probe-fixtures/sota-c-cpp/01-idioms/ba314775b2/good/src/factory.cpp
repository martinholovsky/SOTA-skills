#include <memory>
#include "widget.hpp"

std::unique_ptr<Widget> make_widget(const Config& cfg) {
    auto w = std::make_unique<Widget>(cfg);
    return w;
}
