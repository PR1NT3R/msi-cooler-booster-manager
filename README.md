### What is this?

This is basically a very simple script which piggybacks off [msi-ec](https://github.com/BeardOverflow/msi-ec) to:
 - read the cpu and gpu temp
 - read and manage the coolerboost state

 ### Who is this for?

These 2 scripts are for people who have msi laptops that also run linux.

### Why?

In MControlCenter which also uses said [msi-ec](https://github.com/BeardOverflow/msi-ec), the fan curves don't seem to work for me, and I don't want to use the duct tape way of editing a specific file on boot for the fan curves to work.

This has led to my laptop sometimes overheating due to me forgetting to enable the cooler boost.

I think that you get the idea now, basically a very simple script that is meant to run in the background and automatically enables/disables the coolerboost based on temp with proper de-oscillation methods (At least proper in my opinion), to prevent my laptop from overheating ever again.

### Usage

The script uses `os.getcwd()` to determine the location of the script which talks to msi-ec (main.py), so you need both manager.py and main.py in the same directory

I personally use this crontab. (as sudo of course to be able to modify the file responsible for the coolerboost's state)

`@reboot sleep 30; cd /path/to/the/msi-cooler-booster-manager/ && python3 manager.py`

basically main.py is the subprogram and manager.py is the actual script you are meant to run. (don't question my stupid naming haha)

### Bonus

The main.py file also is perfectly fine on it's own and can be used as a CLI tool!

```
Usage:
    msi-ec-cli --cpu-temp          # Get CPU temperature
    msi-ec-cli --gpu-temp          # Get GPU temperature
    msi-ec-cli --cooler-boost on   # Enable cooler boost
    msi-ec-cli --cooler-boost off  # Disable cooler boost
```