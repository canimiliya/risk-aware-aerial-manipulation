#include <ros/package.h>

#include <iostream>

int main() {
  const std::string path = ros::package::getPath("roslib");
  std::cout << "ros::package::getPath(roslib)=" << path << '\n';
  return path.empty() ? 1 : 0;
}
