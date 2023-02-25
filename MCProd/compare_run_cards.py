import sys

def parse_value(key, value, line):
  if key in [ 'run_tag', 'pdlabel', 'lhaid' ]:
    return value
  try:
    return float(value)
  except ValueError:
    pass
  if value in [ 'T', 'True', '.True.', '.true.' ]:
    return True
  elif value in [ 'F', 'False', '.False.', '.false.' ]:
    return False
  raise ValueError(f"Invalid value in card: {line}")

def load_cards(file):
  card = {}
  with open(file) as f:
    for line in f.readlines():
      line = line.strip()
      if line.startswith('#'): continue
      line = line.split("!")[0].strip()
      if len(line) == 0: continue
      entry = line.split('=')
      if len(entry) != 2:
        raise RuntimeError(f"Invalid line in card: {line}")
      key = entry[1].strip()
      value = entry[0].strip()
      value = parse_value(key, value, line)
      if key in card:
        raise RuntimeError(f"Duplicate entry in card: {line}")
      card[key] = value
  return card

card_1 = load_cards(sys.argv[1])
card_2 = load_cards(sys.argv[2])

all_keys = set(card_1.keys()).union(set(card_2.keys()))

for key in sorted(all_keys):
  if key not in card_1:
    print(f"Only in card 2: {key} = {card_2[key]}")
  elif key not in card_2:
    print(f"Only in card 1: {key} = {card_1[key]}")
  elif card_1[key] != card_2[key]:
    print(f"Different values: {key}: {card_1[key]} vs {card_2[key]}")