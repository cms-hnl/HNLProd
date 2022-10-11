import os
import shutil
import yaml
from RunKit.envToJson import get_cmsenv
from RunKit.sh_tools import sh_call

prod_steps = [ "LHEGEN", "SIM", "DIGIPremix", "HLT", "RECO", "MINIAOD" ]

step_to_file_name = {
  "LHEGEN": "gen",
  "SIM": "sim",
  "DIGIPremix": "raw",
  "HLT": "rawHLT",
  "RECO": "reco",
  "MINIAOD": "miniAOD",
}

def get_step_params(conditions, era, step):
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

def run_prod(gridpack_path, fragment_path, cond_path, era, first_step, last_step, seed, n_evt, output_path,
             previous_output_path, work_dir, remove_outputs=False):
  with open(cond_path, 'r') as f:
    conditions = yaml.safe_load(f)
  if era not in conditions:
    raise RuntimeError(f"Conditions for {era} not found.")
  first_step_index = prod_steps.index(first_step)
  last_step_index = prod_steps.index(last_step)

  os.makedirs(work_dir, exist_ok=True)
  try:
    cmssw_env = {}
    all_step_params = {}
    for step_index, step in enumerate(prod_steps[first_step_index:last_step_index + 1]):
      step_index += first_step_index
      step_out = os.path.join(work_dir, f'{step}.root')
      if os.path.exists(step_out):
        #os.remove(step_out)
        msg = f'{step}.root already exists.'
        if step_index != last_step_index:
          msg += ' Moving to the next step.'
        print(msg)
        continue
      try:
        step_params = get_step_params(conditions, era, step)
        all_step_params[step] = step_params
        cmssw = step_params['CMSSW']
        cmssw_dir = os.path.join(os.environ['ANALYSIS_PATH'], 'soft', 'CentOS7', cmssw)
        if cmssw not in cmssw_env:
          cmssw_env[cmssw] = get_cmsenv(cmssw_dir)
          cmssw_env[cmssw]['X509_USER_PROXY'] = os.environ['X509_USER_PROXY']
          cmssw_env[cmssw]['HOME'] = os.environ['HOME'] if 'HOME' in os.environ else work_dir
        customise_commands = [
          'process.MessageLogger.cerr.FwkReport.reportEvery = 100',
        ]
        cmd = 'cmsDriver.py'
        if step == 'LHEGEN':
          gridpack_path = os.path.abspath(gridpack_path)
          if not os.path.exists(gridpack_path):
            raise RuntimeError(f'gridpack file {gridpack_path} not found.')

          fragment_dir, fragment_name = os.path.split(fragment_path)
          fragment_link = os.path.join('Configuration', 'GenProduction', 'python', fragment_name)
          fragment_link_path = os.path.join(cmssw_dir, 'src', fragment_link)
          if not os.path.exists(fragment_link_path):
            os.symlink(os.path.join(os.environ['ANALYSIS_PATH'], fragment_path), fragment_link_path)

          cmd += f' {fragment_link}'
          customise_commands.extend([
            f'process.RandomNumberGeneratorService.externalLHEProducer.initialSeed=int({seed})',
            f'process.externalLHEProducer.args = cms.vstring("{gridpack_path}")',
            f'process.source.firstRun = cms.untracked.uint32({seed})',
            f'process.generator.comEnergy = cms.double({step_params["comEnergy"]})',
          ])

        if step in [ 'LHEGEN', 'SIM' ]:
          cmd += f' --beamspot {step_params["beamspot"]}'

        cmd += f' --python_filename {step}.py --eventcontent {step_params["eventcontent"]}'
        cmd += f' --datatier {step_params["datatier"]} --fileout file:{step}.root --conditions {step_params["GlobalTag"]}'
        cmd += f' --step {step_params["step"]} --geometry {step_params["geometry"]} --era {step_params["era"]}'
        cmd += f' --mc -n {n_evt}'
        if step_params.get('runUnscheduled', False):
          cmd += ' --runUnscheduled'
        if 'procModifiers' in step_params:
          cmd += ' --procModifiers ' + step_params['procModifiers']
        if step_index > 0:
          if step_index == first_step_index:
            cmd += f' --filein file:{previous_output_path}'
          else:
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
        if step_index == last_step_index:
          output_module = step_params["eventcontent"].split(',')[0]
          output_module += 'output'
          customise_commands.append(f'process.{output_module}.compressionAlgorithm = cms.untracked.string("LZMA")')
          customise_commands.append(f'process.{output_module}.compressionLevel = cms.untracked.int32(9)')
        customise_cmd = '\\n'.join(customise_commands)
        cmd += f" --customise_commands '{customise_cmd}'"

        sh_call([cmd], shell=True, env=cmssw_env[cmssw], cwd=work_dir, verbose=1)

      except:
        if os.path.exists(step_out):
          os.remove(step_out)
        raise

    os.makedirs(output_path, exist_ok=True)
    shutil.copy(os.path.join(work_dir, f'{last_step}.root'),
                os.path.join(output_path, f'{step_to_file_name[last_step]}_{seed}.root'))
    return all_step_params, cmssw_env
  finally:
    if remove_outputs:
      for step in prod_steps[:last_step_index + 1]:
        step_out = os.path.join(work_dir, f'{step}.root')
        if os.path.exists(step_out):
          os.remove(step_out)


if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Run HNL dataset production.')
  parser.add_argument('--gridpack', required=True, type=str, help="path to gridpack dir")
  parser.add_argument('--fragment', required=True, type=str, help="path to gen fragment")
  parser.add_argument('--cond', required=True, type=str, help="path to yaml with conditions")
  parser.add_argument('--era', required=True, type=str, help="era")
  parser.add_argument('--first-step', required=False, default="LHEGEN", type=str,
                      help="first step: " + ', '.join(prod_steps))
  parser.add_argument('--last-step', required=True, type=str, help="final step: " + ', '.join(prod_steps))
  parser.add_argument('--seed', required=True, type=int, help="random seed")
  parser.add_argument('--n-evt', required=True, type=int, help="number of events to generate")
  parser.add_argument('--output', required=True, type=str, help="path to store output root file")
  parser.add_argument('--previous-output', required=False, default=None, type=str,
                      help="path of the root file with the output of the last step before first_step")
  parser.add_argument('--work-dir', required=True, type=str, help="path where to store intermediate outputs")
  args = parser.parse_args()

  run_prod(args.gridpack, args.fragment, args.cond, args.era, args.first_step, args.last_step, args.seed, args.n_evt,
           args.output, args.previous_output, args.work_dir)