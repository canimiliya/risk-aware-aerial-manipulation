#include <pybind11/embed.h>

#include <Python.h>

#include <iostream>

namespace py = pybind11;

int main() {
  try {
    py::scoped_interpreter interpreter{};
    py::module_ sys = py::module_::import("sys");
    py::module_ torch = py::module_::import("torch");
    std::cout << "Py_GetVersion=" << Py_GetVersion() << '\n';
    std::cout << "sys.version=" << std::string(py::str(sys.attr("version"))) << '\n';
    std::cout << "sys.prefix=" << std::string(py::str(sys.attr("prefix"))) << '\n';
    std::cout << "sys.exec_prefix=" << std::string(py::str(sys.attr("exec_prefix"))) << '\n';
    std::cout << "sys.executable=" << std::string(py::str(sys.attr("executable"))) << '\n';
    std::cout << "sys.path=" << std::string(py::str(sys.attr("path"))) << '\n';
    std::cout << "filesystem_encoding=" << std::string(py::str(sys.attr("getfilesystemencoding")())) << '\n';
    std::cout << "default_encoding=" << std::string(py::str(sys.attr("getdefaultencoding")())) << '\n';
    std::cout << "torch.__version__=" << std::string(py::str(torch.attr("__version__"))) << '\n';
    std::cout << "torch.cuda.is_available=" << std::string(py::str(torch.attr("cuda").attr("is_available")())) << '\n';
    std::cout << "torch.cuda.get_device_name=" << std::string(py::str(torch.attr("cuda").attr("get_device_name")(0))) << '\n';
    std::cout << "torch.cuda.get_device_capability=" << std::string(py::str(torch.attr("cuda").attr("get_device_capability")(0))) << '\n';
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "probe_error=" << error.what() << '\n';
    return 1;
  }
}
