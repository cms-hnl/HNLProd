import os
import re
import shutil
import sys

if __name__ == "__main__":
  file_dir = os.path.dirname(os.path.abspath(__file__))
  sys.path.append(os.path.dirname(file_dir))
  __package__ = 'MCProd'

from RunKit.sh_tools import sh_call
from .mk_prodcard import ProdCard

def find_gridpack(path, prod_card_name):
  tarballs = []
  name_pattern = re.compile(f'{prod_card_name}_(.*)_tarball.tar.xz')
  for file in os.listdir(path):
    match = name_pattern.match(file)
    if match:
      tarballs.append((file, match.group(1)))
  if len(tarballs) == 0:
    raise RuntimeError(f'{prod_card_name}: gridpack tarball not found.')
  if len(tarballs) > 1:
    raise RuntimeError(f'{prod_card_name}: multiple gridpack tarballs are found.')
  return tarballs[0]


def mk_gridpack(prodcard_dir, central_output_dir, gen_era):
  ana_path = os.environ['ANALYSIS_PATH']
  gen_path = os.path.join(ana_path, 'genproductions', 'bin', 'MadGraph5_aMCatNLO')
  params = 'params.json'
  prod_card = ProdCard.from_json(os.path.join(prodcard_dir, params))

  def rm_files():
    for file in os.listdir(gen_path):
      if file.startswith(prod_card.name):
        file_path = os.path.join(gen_path, file)
        if os.path.isfile(file_path):
          os.remove(file_path)
        else:
          shutil.rmtree(file_path)

  rm_files()

  cmd = f'./gridpack_generation.sh "{prod_card.name}" "{os.path.relpath(prodcard_dir, start=gen_path)}" "{gen_era}"'
  run_singularity = os.environ['OS_VERSION'] != 'CentOS7'
  if run_singularity:
    cmd = f'/cvmfs/cms.cern.ch/common/cmssw-cc7 --command-to-run bash ' + cmd
  sh_call([cmd], shell=True, cwd=gen_path, env={}, verbose=1)

  run_log = prod_card.name + '.log'
  gridpack, cond = find_gridpack(gen_path, prod_card.name)

  output = os.path.join(central_output_dir, prod_card.name)

  os.makedirs(output, exist_ok=True)
  shutil.move(os.path.join(gen_path, run_log), os.path.join(output, f'{prod_card.name}_{cond}.log'))
  shutil.move(os.path.join(gen_path, gridpack), os.path.join(output, gridpack))
  shutil.copy(os.path.join(prodcard_dir, params), os.path.join(output, params))

  rm_files()


if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Create HNL gridpack.')
  parser.add_argument('--prodcard', required=True, type=str, help="path to prodcard")
  parser.add_argument('--output', required=True, type=str, help="output path with all gridpacks are stored")
  parser.add_argument('--gen-era', required=True, type=str, help="gen era: 2017 or run3")
  args = parser.parse_args()

  mk_gridpack(args.prodcard, args.output, args.gen_era)
