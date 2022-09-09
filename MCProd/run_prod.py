import os
import shutil
import yaml
from RunKit.envToJson import get_cmsenv
from RunKit.sh_tools import sh_call
from mk_prodcard import ProdCard

prod_steps = [ "LHEGEN", "SIM", "DIGIPremix", "HLT", "RECO", "MINIAOD" ]

file_names = {
  "LHEGEN": "gen",
  "SIM": "sim",
  "DIGIPremix": "raw",
  "HLT": "rawHLT",
  "RECO": "reco",
  "MINIAOD": "miniAOD",
}

def run_prod(gridpack_path, fragment_path, cond_path, era, last_step, seed, n_evt, output_path, work_dir):
  #prod_card = ProdCard.from_json(os.path.join(gridpack_path, 'params.json'))
  with open(cond_path, 'r') as f:
    conditions = yaml.safe_load(f)
  if era not in conditions:
    raise RuntimeError(f"Conditions for {era} not found.")
  last_step_index = prod_steps.index(last_step)

  gridpack_path = os.path.abspath(gridpack_path)
  if not os.path.exists(gridpack_path):
    raise RuntimeError(f'gridpack file {gridpack_path} not found.')

  os.makedirs(work_dir, exist_ok=True)
  def get_step_params(step):
    params = {}
    if 'default' in conditions:
      params.update(conditions['default'])
    if 'default_step' in conditions and step in conditions['default_step']:
      params.update(conditions['default_step'][step])
    if 'default' in conditions[era]:
      params.update(conditions[era]['default'])
    if step in conditions[era]:
      params.update(conditions[era][step])
    return params

  cmssw_env = {}
  for step_index, step in enumerate(prod_steps[:last_step_index + 1]):
    step_out = os.path.join(work_dir, f'{step}.root')
    if os.path.exists(step_out):
      #os.remove(step_out)
      print(f'{step}.root already exists. Moving to the next step.')
      continue
    try:
      step_params = get_step_params(step)
      cmssw = step_params['CMSSW']
      cmssw_dir = os.path.join(os.environ['ANALYSIS_PATH'], 'soft', 'CentOS7', cmssw)
      if cmssw not in cmssw_env:
        cmssw_env[cmssw] = get_cmsenv(cmssw_dir)
        cmssw_env[cmssw]['X509_USER_PROXY'] = os.environ['X509_USER_PROXY']
        cmssw_env[cmssw]['HOME'] = os.environ['HOME']
      customise_commands = [ f'process.RandomNumberGeneratorService.externalLHEProducer.initialSeed=int({seed})' ]
      cmd = 'cmsDriver.py'
      if step == 'LHEGEN':
        fragment_dir, fragment_name = os.path.split(fragment_path)
        fragment_link = os.path.join('Configuration', 'GenProduction', 'python', fragment_name)
        fragment_link_path = os.path.join(cmssw_dir, 'src', fragment_link)
        if not os.path.exists(fragment_link_path):
          os.symlink(os.path.join(os.environ['ANALYSIS_PATH'], fragment_path), fragment_link_path)

        cmd += f' {fragment_link}'
        customise_commands.append(f'process.externalLHEProducer.args = cms.vstring(\"{gridpack_path}\")')

      cmd += f' --python_filename {step}.py --eventcontent {step_params["eventcontent"]}'
      cmd += f' --datatier {step_params["datatier"]} --fileout file:{step}.root --conditions {step_params["GlobalTag"]}'
      cmd += f' --step {step_params["step"]} --geometry {step_params["geometry"]} --era {step_params["era"]}'
      cmd += f' --mc -n {n_evt}'
      if step_params.get('runUnscheduled', False):
        cmd += ' --runUnscheduled'
      if 'procModifiers' in step_params:
        cmd += ' --procModifiers ' + step_params['procModifiers']
      if step_index > 0:
        cmd += f' --filein file:{prod_steps[step_index - 1]}.root'
      if 'datamix' in step_params:
        cmd += ' --datamix ' + step_params['datamix']
      if 'pileup_input' in step_params:
        cmd += f' --pileup_input "{step_params["pileup_input"]}"'
      for cmd_type in [ 'inputCommands', 'outputCommand' ]:
        cmds = step_params.get(cmd_type, [])
        if len(cmds) > 0:
          cmd += f' --{cmd_type} "{",".join(cmds)}"'
      cmd += ''.join(' --customise ' + x for x in step_params.get('customise', []))
      customise_commands.extend(step_params.get('customise_commands', []))
      customise_cmd = '; '.join(customise_commands)
      cmd += f" --customise_commands '{customise_cmd}'"

      sh_call([cmd], shell=True, env=cmssw_env[cmssw], cwd=work_dir, verbose=1)
    except:
      if os.path.exists(step_out):
        os.remove(step_out)
      raise

  os.makedirs(output_path, exist_ok=True)
  shutil.copy(os.path.join(work_dir, f'{last_step}.root'),
              os.path.join(output_path, f'{file_names[last_step]}_{seed}.root'))


if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Run HNL dataset production.')
  parser.add_argument('--gridpack', required=True, type=str, help="path to gridpack dir")
  parser.add_argument('--fragment', required=True, type=str, help="path to gen fragment")
  parser.add_argument('--cond', required=True, type=str, help="path to yaml with conditions")
  parser.add_argument('--era', required=True, type=str, help="era")
  parser.add_argument('--last-step', required=True, type=str, help="final step: " + ', '.join(prod_steps))
  parser.add_argument('--seed', required=True, type=int, help="random seed")
  parser.add_argument('--n-evt', required=True, type=int, help="number of events to generate")
  parser.add_argument('--output', required=True, type=str, help="path to store output root file")
  parser.add_argument('--work-dir', required=True, type=str, help="path where to store intermediate outputs")
  args = parser.parse_args()

  run_prod(args.gridpack, args.fragment, args.cond, args.era, args.last_step, args.seed, args.n_evt, args.output,
           args.work_dir)