# spotify-recapped
Analyze your own extended Spotify listening data for fun. 

## Running it yourself
TBD

## For Devs
TBD

### Testing
```bash
python -m pip install pytest
pytest
```

### Linting
```bash
python -m pip install flake8
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```
