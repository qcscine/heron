#include <atom_data.h>

namespace Scine::UI {
AtomData::AtomData(int id, double x, double y, double z, double dis) : index(id), pos_x(x), pos_y(y), pos_z(z), distance(dis) {
}

void AtomData::setId(int id) {
    index = id;
}
int AtomData::getId() const {
    return index;
}

void AtomData::setPosX(double x) {
    pos_x = x;
}
double AtomData::getPosX() const {
    return pos_x;
}

void AtomData::setPosY(double y) {
    pos_y = y;
}
double AtomData::getPosY() const {
    return pos_y;
}

void AtomData::setPosZ(double z) {
    pos_z = z;
}
double AtomData::getPosZ() const {
    return pos_z;
}

void AtomData::setDistance(double dis) {
    distance = dis;
}
double AtomData::getDistance() const {
    return distance;
}
}