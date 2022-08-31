#pragma once

#include <pybind11/pybind11.h>

#include <haptic_data.h>

namespace Scine::UI {

/// @brief HapticCallback class used to process the haptic signals.
class HapticCallback {
public:
    virtual ~HapticCallback() {}

    /** The method will be called when haptic pen is moved.*/
    virtual void move(HapticData data, double azimuth, double elevation, double zoom) = 0;

    /** The method will be called when the top button is pressed.*/
    virtual void first_button_up() = 0;
    /** The method will be called when the top button is released.*/
    virtual void first_button_down() = 0;

    /** The method will be called when the bottom button is pressed.*/
    virtual void second_button_up() = 0;
    /** The method will be called when the bottom button is released.*/
    virtual void second_button_down(int atom_index) = 0;
};

/// @brief PyHapticCallback class is Python wrapper for HapticCallback.
class PyHapticCallback : public HapticCallback {
    using HapticCallback::HapticCallback;

    /** The method will be called when haptic pen is moved.*/
    virtual void move(HapticData data, double azimuth, double elevation, double zoom) override {
        PYBIND11_OVERLOAD_PURE(void, HapticCallback, move, data, azimuth, elevation, zoom);
    }

    /** The method will be called when the top button is pressed.*/
    virtual void first_button_up() override {
        PYBIND11_OVERLOAD_PURE(void, HapticCallback, first_button_up);
    }

    /** The method will be called when the top button is released.*/
    virtual void first_button_down() override {
        PYBIND11_OVERLOAD_PURE(void, HapticCallback, first_button_down);
    }

    /** The method will be called when the bottom button is pressed.*/
    virtual void second_button_up() override {
        PYBIND11_OVERLOAD_PURE(void, HapticCallback, second_button_up);
    }

    /** The method will be called when the bottom button is released.*/
    virtual void second_button_down(int atom_index) override {
        PYBIND11_OVERLOAD_PURE(void, HapticCallback, second_button_down, atom_index);
    }
};

} // namespace Scine::UI
