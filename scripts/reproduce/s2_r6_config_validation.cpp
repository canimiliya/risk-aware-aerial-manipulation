#include <traj_opt/config.h>

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace
{
void expect_invalid(Config config, const char *name)
{
  try
  {
    config.validateExecutionEnvelope();
  }
  catch (const std::invalid_argument &)
  {
    return;
  }
  throw std::runtime_error(std::string(name) + " was accepted");
}
}

int main()
{
  Config valid;
  valid.UseExecutionEnvelopeBarrier = true;
  valid.ExecutionEnvelopeWeight = 1.0;
  valid.ExecutionEnvelopeTau = 0.1;
  valid.ExecutionEnvelopeCenters = {0.0, 0.0, 0.0};
  valid.ExecutionEnvelopeRadii = {0.1};
  valid.validateExecutionEnvelope();

  Config empty = valid;
  empty.ExecutionEnvelopeCenters.clear();
  empty.ExecutionEnvelopeRadii.clear();
  expect_invalid(empty, "empty enabled centers");
  Config bad_length = valid;
  bad_length.ExecutionEnvelopeCenters = {0.0, 0.0};
  expect_invalid(bad_length, "center length");
  Config bad_radius = valid;
  bad_radius.ExecutionEnvelopeRadii = {-0.1};
  expect_invalid(bad_radius, "negative radius");
  Config bad_tau = valid;
  bad_tau.ExecutionEnvelopeTau = 0.0;
  expect_invalid(bad_tau, "non-positive tau");
  Config bad_weight = valid;
  bad_weight.ExecutionEnvelopeWeight = -1.0;
  expect_invalid(bad_weight, "negative weight");
  std::cout << "S2-R6 config validation PASS\n";
  return 0;
}
