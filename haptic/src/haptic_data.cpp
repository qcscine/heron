#include <haptic_data.h>

namespace Scine::UI {
HapticData::HapticData(double x, double y, double z) : pos_x(x), pos_y(y), pos_z(z) {
}

void HapticData::setPosX(double x) {
    pos_x = x;
}
double HapticData::getPosX() const {
    return pos_x;
}

void HapticData::setPosY(double y) {
    pos_y = y;
}
double HapticData::getPosY() const {
    return pos_y;
}

void HapticData::setPosZ(double z) {
    pos_z = z;
}
double HapticData::getPosZ() const {
    return pos_z;
}
}