#pragma once

namespace Scine::UI {

/// @brief HapticData class used to transmit haptic data.
class HapticData {
private:
    double pos_x;
    double pos_y;
    double pos_z;
public:
    /** Default constructor.*/
    explicit HapticData(double x, double y, double z);

    /** Set the x coordinate of the haptic device.*/
    void setPosX(double x);
    /** Set the x coordinate of the haptic device.*/
    double getPosX() const;

    /** Set the y coordinate of the haptic device.*/
    void setPosY(double y);
    /** Set the y coordinate of the haptic device.*/
    double getPosY() const;

    /** Set the z coordinate of the haptic device.*/
    void setPosZ(double z);
    /** Set the z coordinate of the haptic device.*/
    double getPosZ() const;
};
} // namespace Scine::UI
