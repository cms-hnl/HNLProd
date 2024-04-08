import os
import shutil
import yaml
from RunKit.envToJson import get_cmsenv
from RunKit.run_tools import ps_call
from RunKit.grid_tools import gfal_copy_safe

step_to_file_name = {
  "LHEGEN": "gen",
  "SIM": "sim",
  "LHEGS": "sim",
  "DIGIPremix": "raw",
  "HLT": "rawHLT",
  "DIGIPremixHLT": "rawHLT",
  "RECO": "reco",
  "MINIAOD": "miniAOD",
}

singularity_cmds = {
  'CentOS7': '/cvmfs/cms.cern.ch/common/cmssw-cc7',
  'CentOS8': '/cvmfs/cms.cern.ch/common/cmssw-el8',
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
  prod_steps = None
  if 'prod_steps' in conditions[era]:
    prod_steps = conditions[era]['prod_steps']
  elif 'prod_steps' in conditions:
    prod_steps = conditions['prod_steps']
  if prod_steps is None:
    raise RuntimeError(f"Production steps for {era} not found.")
  first_step_index = prod_steps.index(first_step) if first_step else 0
  last_step_index = prod_steps.index(last_step) if last_step else len(prod_steps) - 1

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
        target_os = step_params['OS_VERSION']
        cmssw_key = (cmssw, target_os)
        current_os = os.environ['OS_VERSION']
        sing_cmd = singularity_cmds[target_os] if target_os != current_os else None
        cmssw_dir = os.path.join(os.environ['ANALYSIS_PATH'], 'soft', target_os, cmssw)
        if cmssw_key not in cmssw_env:
          cmssw_env[cmssw_key] = get_cmsenv(cmssw_dir, singularity_cmd=sing_cmd)
          cmssw_env[cmssw_key]['X509_USER_PROXY'] = os.environ['X509_USER_PROXY']
          cmssw_env[cmssw_key]['HOME'] = os.environ['HOME'] if 'HOME' in os.environ else work_dir
          if 'KRB5CCNAME' in os.environ:
            cmssw_env[cmssw_key]['KRB5CCNAME'] = os.environ['KRB5CCNAME']
        customise_commands = [
          'process.MessageLogger.cerr.FwkReport.reportEvery = 100',
        ]
        if sing_cmd:
          env_line = []
          for key in ['PATH', 'LD_LIBRARY_PATH']:
            env_line.append(f'{key}="{cmssw_env[cmssw_key][key]}"')
          env_line = ' '.join(env_line)
          cmd = f"{sing_cmd} --command-to-run env {env_line} "
        else:
          cmd = ''
        cmd += 'cmsDriver.py'
        if step in [ 'LHEGEN', 'LHEGS' ]:
          gridpack_path = os.path.abspath(gridpack_path)
          # if not os.path.exists(gridpack_path):
          #   raise RuntimeError(f'gridpack file {gridpack_path} not found.')

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

        if step in [ 'LHEGEN', 'SIM', 'LHEGS' ]:
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
        if 'pileup' in step_params:
          cmd += ' --pileup ' + step_params['pileup']
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

        # env_line = []
        # for key in ['PATH', 'LD_LIBRARY_PATH']:
        #   env_line.append(f'{key}="{cmssw_env[cmssw_key][key]}"')
        # env_line = ' '.join(env_line)
        # cmd = f"{sing_cmd} --command-to-run env {env_line} "
        # cmd += 'head /eos/home-k/kandroso/cms-hnl/gridpacks/13.6TeV/HeavyNeutrino_trilepton_M-2_V-0.0135_mu_massiveAndCKM_LO/HeavyNeutrino_trilepton_M-2_V-0.0135_mu_massiveAndCKM_LO_slc7_amd64_gcc700_CMSSW_10_6_19_tarball.tar.xz'
        ps_call([cmd], shell=True, env=cmssw_env[cmssw_key], cwd=work_dir, verbose=1)
        # raise RuntimeError('stop')

      except:
        if os.path.exists(step_out):
          os.remove(step_out)
        raise

    if output_path.startswith('/eos/'):
      gfal_copy_safe(os.path.join(work_dir, f'{last_step}.root'),
                'davs://eosuserhttp.cern.ch/' + os.path.join(output_path, f'{step_to_file_name[last_step]}_{seed}.root'))
    else:
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
  parser.add_argument('--first-step', required=False, default=None, type=str, help="first step")
  parser.add_argument('--last-step', required=False, default=None, type=str, help="final step")
  parser.add_argument('--seed', required=True, type=int, help="random seed")
  parser.add_argument('--n-evt', required=True, type=int, help="number of events to generate")
  parser.add_argument('--output', required=True, type=str, help="path to store output root file")
  parser.add_argument('--previous-output', required=False, default=None, type=str,
                      help="path of the root file with the output of the last step before first_step")
  parser.add_argument('--work-dir', required=True, type=str, help="path where to store intermediate outputs")
  args = parser.parse_args()

  run_prod(args.gridpack, args.fragment, args.cond, args.era, args.first_step, args.last_step, args.seed, args.n_evt,
           args.output, args.previous_output, args.work_dir)