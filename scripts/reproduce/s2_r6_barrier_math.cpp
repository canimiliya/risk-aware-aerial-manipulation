#include <Eigen/Core>
#include <se3gcopter/execution_envelope_barrier.h>

#include <cmath>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace
{
void require(const bool condition, const char *message)
{
  if (!condition) throw std::runtime_error(message);
}

double finite_difference(const Eigen::Vector3d &p, const std::vector<double> &centers,
                         const std::vector<double> &radii, const double weight, const double tau,
                         const int axis)
{
  constexpr double h = 1e-7;
  Eigen::Vector3d plus = p;
  Eigen::Vector3d minus = p;
  plus(axis) += h;
  minus(axis) -= h;
  const double fp = ExecutionEnvelopeBarrier::evaluate(plus, weight, tau, centers, radii).cost;
  const double fm = ExecutionEnvelopeBarrier::evaluate(minus, weight, tau, centers, radii).cost;
  return (fp - fm) / (2.0 * h);
}
}  // namespace

int main()
{
  const std::vector<double> centers = {0.0, 0.0, 0.0, 0.001, 0.0, 0.0, -0.001, 0.0, 0.0};
  const std::vector<double> radii = {0.0015, 0.0015, 0.0015};
  const double weight = 10.0;
  const double tau = 2.25e-7;

  const auto at_center = ExecutionEnvelopeBarrier::evaluate(Eigen::Vector3d::Zero(), weight, tau, centers, radii);
  require(std::isfinite(at_center.g) && at_center.g > 0.0, "center must be feasible");
  require(at_center.cost == 0.0 && at_center.gradCost.norm() == 0.0, "feasible cost must be zero");

  const Eigen::Vector3d outside(0.01, 0.002, -0.001);
  const auto at_outside = ExecutionEnvelopeBarrier::evaluate(outside, weight, tau, centers, radii);
  require(std::isfinite(at_outside.g) && at_outside.g < 0.0, "outside point must activate barrier");
  require(std::isfinite(at_outside.cost) && at_outside.cost > 0.0, "outside cost must be finite");
  double max_abs_error = 0.0;
  double max_rel_error = 0.0;
  for (int axis = 0; axis < 3; ++axis)
  {
    const double fd = finite_difference(outside, centers, radii, weight, tau, axis);
    const double analytic = at_outside.gradCost(axis);
    max_abs_error = std::max(max_abs_error, std::abs(fd - analytic));
    max_rel_error = std::max(max_rel_error, std::abs(fd - analytic) / std::max(1.0, std::abs(fd)));
  }
  require(max_abs_error <= 1e-6 || max_rel_error <= 1e-4, "Cartesian gradient mismatch");

  std::vector<double> large_centers;
  std::vector<double> large_radii;
  for (int i = 0; i < 512; ++i)
  {
    large_centers.insert(large_centers.end(), {0.00001 * i, 0.0, 0.0});
    large_radii.push_back(0.0015);
  }
  const auto large = ExecutionEnvelopeBarrier::evaluate(Eigen::Vector3d(0.002, 0.0, 0.0), weight, tau, large_centers, large_radii);
  require(std::isfinite(large.g) && std::isfinite(large.cost) && large.gradCost.allFinite(), "large-N result not finite");

  const auto disabled = ExecutionEnvelopeBarrier::evaluate(Eigen::Vector3d(0.1, 0.1, 0.1), 0.0, tau, centers, radii);
  require(disabled.g == 0.0 && disabled.cost == 0.0 && disabled.gradCost.norm() == 0.0, "disabled regression changed output");

  bool threw = false;
  try { (void)ExecutionEnvelopeBarrier::evaluate(outside, -1.0, tau, centers, radii); } catch (const std::invalid_argument &) { threw = true; }
  require(threw, "negative weight must fail");
  threw = false;
  try { (void)ExecutionEnvelopeBarrier::evaluate(outside, weight, 0.0, centers, radii); } catch (const std::invalid_argument &) { threw = true; }
  require(threw, "non-positive tau must fail");
  threw = false;
  try { (void)ExecutionEnvelopeBarrier::evaluate(outside, weight, tau, {0.0, 0.0}, {0.1}); } catch (const std::invalid_argument &) { threw = true; }
  require(threw, "bad center length must fail");

  std::cout << "S2-R6 barrier math PASS\n"
            << "max_abs_gradient_error=" << max_abs_error << "\n"
            << "max_relative_gradient_error=" << max_rel_error << "\n"
            << "large_N_g=" << large.g << "\n";
  return 0;
}
