#pragma once

namespace Scine::UI {

/// @brief AtomData class used to transmit atom data.
class AtomData {
private:
    int index;
    double pos_x;
    double pos_y;
    double pos_z;
    double distance;
public:
    /** Default constructor.*/
    explicit AtomData(int id, double x, double y, double z, double dis);

    /** Set atom id.*/
    void setId(int id);
    /** Get atom id.*/
    int getId() const;

    /** Set the x coordinate of the atom.*/
    void setPosX(double x);
    /** Get the x coordinate of the atom.*/
    double getPosX() const;

    /** Set the y coordinate of the atom.*/
    void setPosY(double y);
    /** Get the y coordinate of the atom.*/
    double getPosY() const;

    /** Set the z coordinate of the atom.*/
    void setPosZ(double z);
    /** Get the z coordinate of the atom.*/
    double getPosZ() const;

    /** Set the distance between the center of the atom and its edge.
        It is used to check whether the haptic pointer is inside an atom.*/
    void setDistance(double dis);
    /** Get the distance between the center of the atom and its edge.
        It is used to check whether the haptic pointer is inside an atom.*/
    double getDistance() const;
};
} // namespace Scine::UI
