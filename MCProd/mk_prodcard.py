#!/usr/bin/env python

import json
import os
import shutil
from collections import OrderedDict

class ProdCard:
  def __init__(self, type, mass, e_mixing, mu_mixing, tau_mixing):
    self.type = type
    if type.lower() == 'dirac':
      self.pdg_id = '9990012'
      self.model = 'SM_HeavyN_Dirac_CKM_Masses_LO'
      name_suffix = '_Dirac'
    elif type.lower() == 'majorana':
      self.pdg_id = '9900012'
      self.model = 'SM_HeavyN_AllMassive_LO'
      name_suffix = ''
    else:
      raise RuntimeError(f'Unsupported HNL type = "{type}"')

    self.mass = mass
    if mass <= 0:
      raise RuntimeError(f'HNL mass should be a positive number')

    self.name = f'HeavyNeutrino_trilepton_M-{mass}'
    self.mixings = OrderedDict([ ('e', e_mixing), ('mu', mu_mixing), ('tau', tau_mixing)])
    self.positive_mixings = []
    for mix_type, mix_value in self.mixings.items():
      if mix_value < 0:
        raise RuntimeError(f'HNL mixing parameters should be >= 0.')
      if mix_value > 0:
        self.name += f'_V-{mix_value}_{mix_type}'
        self.positive_mixings.append(mix_type)
    if len(self.positive_mixings) == 0:
      raise RuntimeError('At least one HNL mixing parameter shoudl be > 0.')
    self.name += name_suffix + '_massiveAndCKM_LO'

  def to_json(self, json_file):
    params = {
      'type': self.type,
      'mass': self.mass,
      'mixings': dict(self.mixings),
    }
    with open(json_file, 'w') as f:
      json.dump(params, f, indent=2)

  @staticmethod
  def from_json(json_file):
    with open(json_file, 'r') as f:
      params = json.load(f)
    return ProdCard(params['type'], params['mass'], params['mixings'].get('e', 0.), params['mixings'].get('mu', 0.),
                    params['mixings'].get('tau', 0.))

def mk_prodcard(templates, central_output_dir, prod_card):
  output_dir = os.path.join(central_output_dir, prod_card.name)
  if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
  os.makedirs(output_dir)

  def copy(file_name, replacements=None):
    file_orig = os.path.join(templates, file_name)
    file_out = os.path.join(output_dir, f'{prod_card.name}_{file_name}')
    if replacements is None:
      shutil.copyfile(file_orig, file_out)
    else:
      with open(file_orig, 'r') as f:
        data = f.read()
      for key, value in replacements.items():
        data = data.replace(key, value)
      with open(file_out, 'w') as f:
        f.write(data)

  for file in ['madspin_card.dat', 'run_card.dat']:
    copy(file)

  custom_repl = {
    'PDGID': prod_card.pdg_id,
    'MASS': str(prod_card.mass),
  }
  for mix_type, mix_value in prod_card.mixings.items():
    custom_repl[mix_type.upper() + '_MIXING'] = f'{mix_value:.6e}'
  copy('customizecards.dat', custom_repl)

  proc_repl = {
    'MODEL': prod_card.model,
    'NAME': prod_card.name,
  }
  for l_name, l_sign in [ ('LPLUS', '+'), ('LMINUS', '-') ]:
    proc_repl[l_name] = ' '.join([ x[:2] + l_sign for x in prod_card.positive_mixings ])
  copy('proc_card.dat', proc_repl)

  copy('extramodels.dat', { 'MODEL': prod_card.model })

  prod_card.to_json(os.path.join(output_dir, 'params.json'))


if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Create HNL prodcards.')
  parser.add_argument('--templates', required=True, type=str, help="path to prodcard templates")
  parser.add_argument('--output', required=True, type=str, help="output path with all prodcards")
  parser.add_argument('--type', required=True, type=str, help="HNL type: dirac or majorana")
  parser.add_argument('--mass', required=True, type=float, help="HNL mass (GeV)")
  parser.add_argument('--e-mixing', required=True, type=float, help="HNL-nu_e mixing parameter")
  parser.add_argument('--mu-mixing', required=True, type=float, help="HNL-nu_mu mixing parameter")
  parser.add_argument('--tau-mixing', required=True, type=float, help="HNL-nu_tau mixing parameter")
  args = parser.parse_args()

  prod_card = ProdCard(args.type, args.mass, args.e_mixing, args.mu_mixing, args.tau_mixing)
  mk_prodcard(args.templates, args.output, prod_card)
