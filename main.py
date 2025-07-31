#!/usr/bin/env python3
"""
msi_ec cli tool with the only purpose of keeping the temps low via use of automated tooling
Based on the BeardOverflow/msi-ec kernel driver

Usage:
    msi-ec-cli --cpu-temp          # Get CPU temperature
    msi-ec-cli --gpu-temp          # Get GPU temperature
    msi-ec-cli --cooler-boost on   # Enable cooler boost
    msi-ec-cli --cooler-boost off  # Disable cooler boost
"""

import argparse
from pathlib import Path
import sys

class MSIECController:
    MSI_EC_BASE_PATH = Path("/sys/devices/platform/msi-ec")
    
    def __init__(self):
        self.base_path = self.MSI_EC_BASE_PATH
        
    def _check_driver_availability(self):
        if not self.base_path.exists():
            raise FileNotFoundError(
                "MSI EC driver not found. Please ensure the msi-ec kernel module is loaded.\n"
                "Installation: https://github.com/BeardOverflow/msi-ec"
            )
    
    def _read_sysfs_file(self, filepath):
        try:
            with open(filepath, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {filepath}")
        except PermissionError:
            raise PermissionError(f"Permission denied reading: {filepath}")
        except Exception as e:
            raise Exception(f"Error reading {filepath}: {e}")
    
    def _write_sysfs_file(self, filepath, value):
        try:
            with open(filepath, 'w') as f:
                f.write(str(value))
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {filepath}")
        except PermissionError:
            raise PermissionError(f"Permission denied writing to: {filepath}. Try running with sudo.")
        except Exception as e:
            raise Exception(f"Error writing to {filepath}: {e}")
    
    def get_cpu_temperature(self):
        """This is only gonna be in C because that is how the driver outputs it"""
        self._check_driver_availability()
        temp_file = self.base_path / "cpu" / "realtime_temperature"
        temp_raw = self._read_sysfs_file(temp_file)
        
        try:
            temp_celsius = int(temp_raw)
            return f"{temp_celsius}.0°C"
        except ValueError:
            raise ValueError(f"Invalid temperature value: {temp_raw}")
    
    def get_gpu_temperature(self):
        """This is only gonna be in C because that is how the driver outputs it"""
        self._check_driver_availability()
        temp_file = self.base_path / "gpu" / "realtime_temperature"
        temp_raw = self._read_sysfs_file(temp_file)
        
        try:
            temp_celsius = int(temp_raw)
            return f"{temp_celsius}.0°C"
        except ValueError:
            raise ValueError(f"Invalid temperature value: {temp_raw}")
    
    def set_cooler_boost(self, enable):
        self._check_driver_availability()
        cooler_file = self.base_path / "cooler_boost"
        value = "on" if enable else "off"
        self._write_sysfs_file(cooler_file, value)
        return f"Cooler boost {'enabled' if enable else 'disabled'}"
    
    def get_cooler_boost_status(self):
        self._check_driver_availability()
        cooler_file = self.base_path / "cooler_boost"
        status = self._read_sysfs_file(cooler_file)
        return status == "on"


def main():
    parser = argparse.ArgumentParser(
        description="msi_ec cli tool with the only purpose of keeping the temps low via use of automated tooling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --cpu-temp                    # Get CPU temperature
  %(prog)s --gpu-temp                    # Get GPU temperature
  %(prog)s --cooler-boost on             # Enable cooler boost
  %(prog)s --cooler-boost off            # Disable cooler boost
  %(prog)s --status                      # Show all current values

Note: Requires the msi-ec kernel driver to be installed and loaded.
      Some operations may require root privileges (sudo).
        """
    )
    
    parser.add_argument(
        "--cpu-temp",
        action="store_true",
        help="Get CPU temperature"
    )
    
    parser.add_argument(
        "--gpu-temp", 
        action="store_true",
        help="Get GPU temperature"
    )
    
    parser.add_argument(
        "--cooler-boost",
        choices=["on", "off"],
        help="Enable or disable cooler boost"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status of all monitored values"
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 1
    
    controller = MSIECController()
    
    try:
        # Handle temperature requests
        if args.cpu_temp:
            temp = controller.get_cpu_temperature()
            print(f"CPU Temperature: {temp}")
        
        if args.gpu_temp:
            temp = controller.get_gpu_temperature()
            print(f"GPU Temperature: {temp}")
        
        # Handle cooler boost control
        if args.cooler_boost is not None:
            enable = args.cooler_boost == "on"
            result = controller.set_cooler_boost(enable)
            print(result)
        
        # Handle status request
        if args.status:
            print("=== MSI EC Status ===")
            try:
                cpu_temp = controller.get_cpu_temperature()
                print(f"CPU Temperature: {cpu_temp}")
            except Exception as e:
                print(f"CPU Temperature: Error - {e}")
            
            try:
                gpu_temp = controller.get_gpu_temperature()
                print(f"GPU Temperature: {gpu_temp}")
            except Exception as e:
                print(f"GPU Temperature: Error - {e}")
            
            try:
                cooler_status = controller.get_cooler_boost_status()
                print(f"Cooler Boost: {'Enabled' if cooler_status else 'Disabled'}")
            except Exception as e:
                print(f"Cooler Boost: Error - {e}")
    
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except PermissionError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Tip: Try running with sudo for write operations", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())