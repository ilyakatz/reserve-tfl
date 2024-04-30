
## Installation

```bash
apt install python3.11-venv
python3 -m venv tfl 
source tfl/bin/activate
pip install -r prod.txt
```

## Run

```
source tfl/bin/activate
```

```bash
python3 ./reserve_tfl.py --day 2
```

### Debug mode

```bash
python3 ./reserve_tfl.py --debug --day 16
```