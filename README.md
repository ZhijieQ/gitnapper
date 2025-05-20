# Gitnapper

A proof-of-concept ransomware attack targetted towards version control software, running as a Visual Studio Code extension.

## Setup

### Running the Keyserver

Before running the extension, you should set up the keyserver to make sure you can recover a password after the attack has taken place. First create a virtual environment:
```
apt install python3-virtualenv
virtualenv venv
source venv/bin/activate
pip3 install -r requirements.txt
python3 backend/keyserver.py
```

### Running the Extension
* Press `F5` to open a new window with gitnapper loaded, and open a github repository.
* The extension automatically attempts to run the attack when saving a file. You may not see any changes until you make enough changes to your repository before a commit.
* To run the attack manually, open the command palette (`Ctrl+Shift+P` or `Cmd+Shift+P` on Mac) and type `Lint my code!!!`.

## Ransomware Detection

Many experimental ransomware detection scripts can be found in the `scripts` folder.

### Entropy Detector

To view how to run this script, use the following command:
```bash
python3 detection/entropy_detector.py --help
```

### Event Detectors
To use any of the three event detection scripts, you need to install the `inotify-tools` package:
```bash
sudo apt install inotify-tools  # Debian/Ubuntu
sudo yum install inotify-tools  # RHEL/CentOS
sudo pacman -S inotify-tools # Arch
```
You may need to add execute permissions to the scripts before running them: 
```bash
chmod +x scripts/event_detector.sh
chmod +x scripts/event_detector.py
chmod +x scripts/event_detector_block.py
```