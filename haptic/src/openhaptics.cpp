#include <openhaptics.h>

namespace Scine::UI {

/*******************************************************************************
Utilities.
*******************************************************************************/

HapticData HapticDeviceManager::transformToAppCoordinates(const hduVector3Dd& pos,
                                                          const std::vector<std::vector<double>>& transformation_matrix,
                                                          int scale_factor) {
    // transform to application coordinates

    double x = transformation_matrix[0][0] * pos[0] +
               transformation_matrix[0][1] * pos[1] +
               transformation_matrix[0][2] * pos[2] +
               transformation_matrix[0][3];

    double y = transformation_matrix[1][0] * pos[0] +
               transformation_matrix[1][1] * pos[1] +
               transformation_matrix[1][2] * pos[2] +
               transformation_matrix[1][3];

    double z = transformation_matrix[2][0] * pos[0] +
               transformation_matrix[2][1] * pos[1] +
               transformation_matrix[2][2] * pos[2] +
               transformation_matrix[2][3];

    return HapticData(x / scale_factor, y / scale_factor, z / scale_factor);
}

hduVector3Dd HapticDeviceManager::transformToHapticCoordinates(const double& x, const double& y, const double& z,
                                                              const std::vector<std::vector<double>>& invert_matrix,
                                                              int scale_factor) {
    // transform to haptic coordinates

    double new_x = invert_matrix[0][0] * x * scale_factor +
                   invert_matrix[0][1] * y * scale_factor +
                   invert_matrix[0][2] * z * scale_factor +
                   invert_matrix[0][3];

    double new_y = invert_matrix[1][0] * x * scale_factor +
                   invert_matrix[1][1] * y * scale_factor +
                   invert_matrix[1][2] * z * scale_factor +
                   invert_matrix[1][3];

    double new_z = invert_matrix[2][0] * x * scale_factor +
                   invert_matrix[2][1] * y * scale_factor +
                   invert_matrix[2][2] * z * scale_factor +
                   invert_matrix[2][3];

    return hduVector3Dd(new_x, new_y, new_z);
}

double HapticDeviceManager::calculateDistance(const AtomData& atom, const HapticData& data) {
    // calculate distance between atom and haptic pointer
    double x_d = (atom.getPosX() - data.getPosX()) * (atom.getPosX() - data.getPosX());
    double y_d = (atom.getPosY() - data.getPosY()) * (atom.getPosY() - data.getPosY());
    double z_d = (atom.getPosZ() - data.getPosZ()) * (atom.getPosZ() - data.getPosZ());
    return sqrt(x_d + y_d + z_d);
}

int HapticDeviceManager::findClosestAtomIndex(const std::vector<AtomData>& molecule, const HapticData& data) {
    // find closest atom to haptic pointer
    int closest_atom_index = -1;
    double best_d = -1;

    for (auto i = 0; i < molecule.size(); ++i) {
        double d = calculateDistance(molecule[i], data);

        if (closest_atom_index == -1 || d < best_d) {
            closest_atom_index = i;
            best_d = d;
        }
    }
    return closest_atom_index;
}

void HapticDeviceManager::scaleForce(hduVector3Dd& force, const HDdouble anchor_stiffness) {
    hduVecScaleInPlace(force, anchor_stiffness);

    // Check if we need to clamp the force.
    HDdouble force_clamp;
    hdGetDoublev(HD_NOMINAL_MAX_CONTINUOUS_FORCE, &force_clamp);
    if (hduVecMagnitude(force) > force_clamp)
    {
        hduVecNormalizeInPlace(force);
        hduVecScaleInPlace(force, force_clamp);
    }
}

void HapticDeviceManager::setForce(const hduVector3Dd& position,
                                   const hduVector3Dd& atom_pos,
                                   const hduVector3Dd& atom_gradient,
                                   HapticDeviceManager *p_this) {
    // set haptic force
    hduVector3Dd force = { 0, 0, 0 };

    if (p_this->calc_gradient_in_loop && p_this->second_button_down) {
        // set gradient as force if the gradient is calculating and the second button is pressed on one of the atoms
        hduVector3Dd new_pos = { atom_pos[0] - atom_gradient[0], atom_pos[1] - atom_gradient[1], atom_pos[2] - atom_gradient[2]};
        hduVecSubtract(force, new_pos, atom_pos);
        scaleForce(force, 0.8);
    }

    hdSetDoublev(HD_CURRENT_FORCE, force);
}

double HapticDeviceManager::calculateAzimuth(const hduVector3Dd& position, const hduVector3Dd& last_position) {
    // calculate azimuth using real haptic coordinates
    return last_position[0] - position[0];
}

double HapticDeviceManager::calculateElevation(const hduVector3Dd& position, const hduVector3Dd& last_position) {
    // calculate elevation using real haptic coordinates
    return last_position[1] - position[1];
}

double HapticDeviceManager::calculateZoom(const hduVector3Dd& position, const hduVector3Dd& last_position) {
    // calculate zoom using real haptic coordinates
    if (last_position[2] - position[2] <= -1.2) {
        return 0.90;  // zoom out
    } else if (last_position[2] - position[2] >= 1.2) {
        return 1.10; // zoom on
    } else {
        return 1; // do nothing
    }
}

/*******************************************************************************
 Checks the state of the gimbal button and gets the position of the device.
*******************************************************************************/
HDCallbackCode HDCALLBACK HapticDeviceManager::updateDeviceCallback(void *user_data) {
    // Start device update processing
    HapticDeviceManager *p_this = static_cast<HapticDeviceManager *>(user_data);

    // read haptic data
    int current_buttons, last_buttons;
    hduVector3Dd current_position, last_position;
    HDErrorInfo error;

    hdBeginFrame(hdGetCurrentDevice());

    /* Get the current and the last location of the device.
       We declare a vector of three doubles since hdGetDoublev returns
       the information in a vector of size 3. */
    hdGetDoublev(HD_CURRENT_POSITION, current_position);
    hdGetDoublev(HD_LAST_POSITION, last_position);

    /* Retrieve the current button(s). */
    hdGetIntegerv(HD_CURRENT_BUTTONS, &current_buttons);
    hdGetIntegerv(HD_LAST_BUTTONS, &last_buttons);

    /* Also check the error state of HDAPI. */
    if (HD_DEVICE_ERROR(error = hdGetError()))
    {
        hduPrintError(stderr, &error, "Failed to move");
        exit(-1);
    }

    // thread safe copy
    std::vector<AtomData> molecule;
    std::vector<std::vector<double>> transformation_matrix;
    std::vector<std::vector<double>> invert_matrix;
    std::vector<std::vector<double>> gradients;
    {
        std::lock_guard<std::mutex> lock(p_this->molecule_mutex);
        molecule = p_this->molecule;
    }
    {
        std::lock_guard<std::mutex> lock(p_this->matrix_mutex);
        transformation_matrix = p_this->transformation_matrix;
        invert_matrix = p_this->invert_matrix;
    }
    {
        std::lock_guard<std::mutex> lock(p_this->gradient_mutex);
        gradients = p_this->gradient;
    }

    /* convert to app coordinate and scale data scale_factor times */
    HapticData data = transformToAppCoordinates(current_position, transformation_matrix, p_this->scale_factor);

    int selected_atom_id = -1;

    if (molecule.size() > 0) {
        std::vector<double> gradient = {0, 0, 0};
        int closest_atom_index = findClosestAtomIndex(molecule, data);
        auto closest_atom = molecule[closest_atom_index];

        if (calculateDistance(closest_atom, data) <= 3. * closest_atom.getDistance()) {
            selected_atom_id = closest_atom.getId();
            if (selected_atom_id < gradients.size()) {
                gradient = gradients[selected_atom_id];
            }
        }

        hduVector3Dd transformed_atom = transformToHapticCoordinates(closest_atom.getPosX(),
                                                                    closest_atom.getPosY(),
                                                                    closest_atom.getPosZ(),
                                                                    invert_matrix,
                                                                    p_this->scale_factor);

        hduVector3Dd transformed_gradient = transformToHapticCoordinates(gradient[0],
                                                                        gradient[1],
                                                                        gradient[2],
                                                                        invert_matrix,
                                                                        p_this->scale_factor);

        setForce(current_position, transformed_atom, transformed_gradient, p_this);
    }

    /* Detect button state transitions. */
    if ((current_buttons & HD_DEVICE_BUTTON_1) != 0 && (last_buttons & HD_DEVICE_BUTTON_1) == 0) {
        for (auto* callback : p_this->callbacks) {
            p_this->first_button_down = true;
            callback->first_button_down();
        }
    }
    if ((current_buttons & HD_DEVICE_BUTTON_1) != 1 && (last_buttons & HD_DEVICE_BUTTON_1) == 1) {
        for (auto* callback : p_this->callbacks) {
            p_this->first_button_down = false;
            callback->first_button_up();
        }
    }
    if ((current_buttons & HD_DEVICE_BUTTON_2) != 0 && (last_buttons & HD_DEVICE_BUTTON_2) == 0) {
        for (auto* callback : p_this->callbacks) {
            p_this->second_button_down = true;
            callback->second_button_down(selected_atom_id);
        }
    }
    if ((current_buttons & HD_DEVICE_BUTTON_2) != 2 && (last_buttons & HD_DEVICE_BUTTON_2) == 2) {
        for (auto* callback : p_this->callbacks) {
            p_this->second_button_down = false;
            callback->second_button_up();
        }
    }

    hdEndFrame(hdGetCurrentDevice());

    // reduce move callback counts
    constexpr int kMaxEventsPerSecond = 60;
    constexpr auto kMinDelay = std::chrono::microseconds(1000000) / kMaxEventsPerSecond;
    auto now = std::chrono::steady_clock::now();
    if (now - p_this->last_event_timestamp < kMinDelay) {
        return HD_CALLBACK_CONTINUE;
    }
    p_this->last_event_timestamp = now;

    // init last_send_data
    if (p_this->call_first_time) {
        p_this->call_first_time = false;
        p_this->last_send_data = last_position;
    }

    HapticData last_data = transformToAppCoordinates(p_this->last_send_data, transformation_matrix, p_this->scale_factor);

    // calculate camera movement
    double azimuth = calculateAzimuth(current_position, p_this->last_send_data);
    double elevation = calculateElevation(current_position, p_this->last_send_data);
    double zoom = calculateZoom(current_position, p_this->last_send_data);

    if (data.getPosX() != last_data.getPosX() ||
        data.getPosY() != last_data.getPosY() ||
        data.getPosZ() != last_data.getPosZ() ) {
        for (auto* callback : p_this->callbacks) {
            callback->move(data, azimuth, elevation, zoom);
        }
    }

    // update last_send_data
    p_this->last_send_data = current_position;

    return HD_CALLBACK_CONTINUE;
}

/*******************************************************************************
 Initializes the HDAPI.  This involves initing a device configuration, enabling
 forces, and scheduling a haptic thread callback for servicing the device.
*******************************************************************************/
bool HapticDeviceManager::init_haptic_device() {

    HDErrorInfo error;

    ghHD = hdInitDevice(HD_DEFAULT_DEVICE);
    if (HD_DEVICE_ERROR(error = hdGetError()))
    {
        hduPrintError(stderr, &error, "Failed to initialize haptic device");
        return false;
    }

    hdEnable(HD_FORCE_OUTPUT);

    hUpdateDeviceCallback = hdScheduleAsynchronous(updateDeviceCallback, this, HD_DEFAULT_SCHEDULER_PRIORITY);

    hdStartScheduler();
    if (HD_DEVICE_ERROR(error = hdGetError()))
    {
        hduPrintError(stderr, &error, "Failed to start the scheduler");
        return false;
    }
    return true;
}

/*******************************************************************************
Add callback.
*******************************************************************************/
void HapticDeviceManager::add_haptic_callback(HapticCallback* callback) {
    callbacks.push_back(callback);
}

/*******************************************************************************
Clear molecule.
*******************************************************************************/
void HapticDeviceManager::clear_molecule() {
    std::lock_guard<std::mutex> lock(molecule_mutex);
    molecule.clear();
}

/*******************************************************************************
Add atom.
*******************************************************************************/
void HapticDeviceManager::add_atom(AtomData atom) {
    std::lock_guard<std::mutex> lock(molecule_mutex);
    molecule.push_back(atom);
}

/*******************************************************************************
Update atom.
*******************************************************************************/
void HapticDeviceManager::update_atom(AtomData atom) {
    std::lock_guard<std::mutex> lock(molecule_mutex);
    molecule[atom.getId()] = atom;
}

/*******************************************************************************
Update gradient.
*******************************************************************************/
void HapticDeviceManager::set_calc_gradient_in_loop(bool gradient_in_loop) {
    std::lock_guard<std::mutex> lock(gradient_mutex);
    calc_gradient_in_loop = gradient_in_loop;
}

void HapticDeviceManager::update_gradient(pybind11::list gradient_list) {
    std::lock_guard<std::mutex> lock(gradient_mutex);

    for (auto i = gradient.size(); i < gradient_list.size() / 3; ++i) {
        gradient.push_back(std::vector<double>(3));
    }

    int index = 0;
    for (auto value : gradient_list) {
        gradient[index / 3][index % 3] = pybind11::cast<double>(value);
        ++index;
    }
}

/*******************************************************************************
Update transformation matrix.
*******************************************************************************/
void HapticDeviceManager::set_transformation_matrix(pybind11::list t_matrix,
                                                    pybind11::list i_matrix) {
    std::lock_guard<std::mutex> lock(matrix_mutex);

    int index = 0;
    for (auto value : t_matrix) {
        transformation_matrix[index / 4][index % 4] = pybind11::cast<double>(value);
        ++index;
    }

    index = 0;
    for (auto value : i_matrix) {
        invert_matrix[index / 4][index % 4] = pybind11::cast<double>(value);
        ++index;
    }
}

/*******************************************************************************
 This handler will get called when the application is exiting. This is our
 opportunity to cleanly shutdown the HD API.
*******************************************************************************/
void HapticDeviceManager::exit_haptic_device() {
    hdStopScheduler();
    hdUnschedule(hUpdateDeviceCallback);

    if (ghHD != HD_INVALID_HANDLE)
    {
        hdDisableDevice(ghHD);
        ghHD = HD_INVALID_HANDLE;
    }
}

} // namespace Scine::UI
