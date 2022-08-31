#pragma once

#include <pybind11/pybind11.h>
#include <vector>
#include <mutex>
#include <chrono>
#include <HD/hd.h>
#include <HDU/hduError.h>
#include <HDU/hduVector.h>
#include <haptic_callback.h>
#include <atom_data.h>

namespace Scine::UI {

/// @brief HapticDeviceManager class used to communicate with haptic device.
class HapticDeviceManager {

private:
    HHD ghHD = HD_INVALID_HANDLE;
    HDSchedulerHandle hUpdateDeviceCallback = HD_INVALID_HANDLE;

    const int scale_factor = 10;
    bool calc_gradient_in_loop = false;
    bool first_button_down = false;
    bool second_button_down = false;
    bool call_first_time = true; // use to init data when updateDeviceCallback called for the first time
    hduVector3Dd last_send_data; // last data that was send to GUI
    std::vector<std::vector<double>> transformation_matrix = {{1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}, {0, 0, 0, 1}};
    std::vector<std::vector<double>> invert_matrix = {{1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}, {0, 0, 0, 1}};
    std::vector<std::vector<double>> gradient = {};
    std::vector<HapticCallback*> callbacks = {};
    std::vector<AtomData> molecule = {};

    std::mutex molecule_mutex; // protects molecule
    std::mutex gradient_mutex; // protects gradient
    std::mutex matrix_mutex; // transformation_matrix and invert_matrix

    std::chrono::time_point<std::chrono::steady_clock> last_event_timestamp;

    /** Convert from haptic coordinats to application coordinats.*/
    static HapticData transformToAppCoordinates(const hduVector3Dd& pos, const std::vector<std::vector<double>>& transformation_matrix, int scale_factor);
    /** Convert from application coordinats to haptic coordinats.*/
    static hduVector3Dd transformToHapticCoordinates(const double& x, const double& y, const double& z, const std::vector<std::vector<double>>& invert_matrix, int scale_factor);
    /** Calculate distance between atom and pointer.*/
    static double calculateDistance(const AtomData& atom, const HapticData& data);
    /** Find closest atom to haptic pointer.*/
    static int findClosestAtomIndex(const std::vector<AtomData>& molecule, const HapticData& data);
    /** Scale force.*/
    static void scaleForce(hduVector3Dd& force, const HDdouble anchor_stiffness);
    /** Set haptic force.*/
    static void setForce(const hduVector3Dd& position, const hduVector3Dd& closest_atom, const hduVector3Dd& atom_gradient, HapticDeviceManager *p_this);

    static double calculateAzimuth(const hduVector3Dd& position, const hduVector3Dd& last_position);
    static double calculateElevation(const hduVector3Dd& position, const hduVector3Dd& last_position);
    static double calculateZoom(const hduVector3Dd& position, const hduVector3Dd& last_position);

    static HDCallbackCode HDCALLBACK updateDeviceCallback(void *user_data);

public:
    /** Init haptic device.*/
    bool init_haptic_device();
    /** Add callback for haptic device.*/
    void add_haptic_callback(HapticCallback* callback);
    /** Deinitializate haptic device.*/
    void exit_haptic_device();

    // molecule API
    /** Clear molecule.*/
    void clear_molecule();
    /** Add atom to molecule.*/
    void add_atom(AtomData atom);
    /** Update atom in molecule.*/
    void update_atom(AtomData atom);
    /** Update gradient.*/
    void update_gradient(pybind11::list gradient_list);
    /** Set calculate gradient in the loop.*/
    void set_calc_gradient_in_loop(bool gradient_in_loop);
    /** Set camera transformation matrix and invert transformation matrix.*/
    void set_transformation_matrix(pybind11::list t_matrix, pybind11::list i_matrix);
};
} // namespace Scine::UI
