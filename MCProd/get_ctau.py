import tarfile
import re

def get_width(pdgid, gridpack_path):
  '''Get width in GeV of HNL from gridpack.'''
  pattern = re.compile(f'DECAY +{pdgid} +([^ ]+)\n')
  with tarfile.open(gridpack_path, 'r:xz') as tar:
    with tar.extractfile('process/madevent/Cards/param_card.dat') as file:
      lines = file.readlines()
    for line in lines:
      line = line.decode('utf-8')
      match = pattern.match(line)
      if match:
        return float(match.group(1))
  raise RuntimeError(f'Could not find width for pdgid {pdgid} in gridpack {gridpack_path}.')

if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Get width and ctau.')
  parser.add_argument('pdgid', nargs=1, type=str, help="pdg id of HNL")
  parser.add_argument('gridpack', nargs=1, type=str, help="path to gridpack")

  args = parser.parse_args()

  width = get_width(args.pdgid[0], args.gridpack[0])
  c = 299792458.0 # m/s
  h_bar = 6.582119569e-25 # GeV s
  ctau = c * h_bar / width * 1e3 # mm
  print(f'width = {width:.6e} GeV')
  print(f'ctau = {ctau:.4f} mm')