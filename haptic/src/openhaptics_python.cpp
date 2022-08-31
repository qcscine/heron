#include <pybind11/pybind11.h>
#include <openhaptics.h>

using namespace Scine::UI;

PYBIND11_MODULE(scine_heron_haptic, mod) {
    mod.doc() = "Pybind11 Bindings for SCINE UI HAPTIC";

    pybind11::class_<HapticCallback, PyHapticCallback>(mod, "HapticCallback")
        .def(pybind11::init<>())
        .def("move", &HapticCallback::move)
        .def("first_button_down", &HapticCallback::first_button_down)
        .def("first_button_up", &HapticCallback::first_button_up)
        .def("second_button_down", &HapticCallback::second_button_down)
        .def("second_button_up", &HapticCallback::second_button_up);

    pybind11::class_<HapticData>(mod, "HapticData")
        .def(pybind11::init<double, double, double>(),
             pybind11::arg("x") = 0,
             pybind11::arg("y") = 0,
             pybind11::arg("z") = 0, "Initialize hatic data")
        .def_property("x", &HapticData::getPosX, &HapticData::setPosX, "")
        .def_property("y", &HapticData::getPosY, &HapticData::setPosY, "")
        .def_property("z", &HapticData::getPosZ, &HapticData::setPosZ, "");

    pybind11::class_<AtomData>(mod, "AtomData")
        .def(pybind11::init<int, double, double, double, double>(),
             pybind11::arg("id") = 0,
             pybind11::arg("x") = 0,
             pybind11::arg("y") = 0,
             pybind11::arg("z") = 0,
             pybind11::arg("dis") = 0, "Initialize hatic data")
        .def_property("id", &AtomData::getId, &AtomData::setId, "")
        .def_property("x", &AtomData::getPosX, &AtomData::setPosX, "")
        .def_property("y", &AtomData::getPosY, &AtomData::setPosY, "")
        .def_property("z", &AtomData::getPosZ, &AtomData::setPosZ, "")
        .def_property("dis", &AtomData::getDistance, &AtomData::setDistance, "");

    pybind11::class_<HapticDeviceManager>(mod, "HapticDeviceManager")
        .def(pybind11::init<>())
        .def("init_haptic_device", &HapticDeviceManager::init_haptic_device, "Connect to haptic device.")
        .def("add_haptic_callback", &HapticDeviceManager::add_haptic_callback, "Add haptic device callback.")
        .def("exit_haptic_device", &HapticDeviceManager::exit_haptic_device, "Disconnect haptic device.")
        .def("clear_molecule", &HapticDeviceManager::clear_molecule, "Clear molecule.")
        .def("add_atom", &HapticDeviceManager::add_atom, "Add atom in molecule.")
        .def("update_atom", &HapticDeviceManager::update_atom, "Update atom in molecule.")
        .def("set_transformation_matrix", &HapticDeviceManager::set_transformation_matrix, "Update transformation matrix.")
        .def("set_calc_gradient_in_loop", &HapticDeviceManager::set_calc_gradient_in_loop, "True if gradient calc in loop otherwise False.")
        .def("update_gradient", &HapticDeviceManager::update_gradient, "Update gradient.");
}
