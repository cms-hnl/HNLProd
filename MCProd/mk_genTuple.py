import glob
import os
import shutil
from RunKit.run_tools import ps_call
from RunKit.envToJson import get_cmsenv

def mk_genTuple(input, output, source, config, cmssw, verbose):
  if verbose > 0:
    print(f'Processing "{input}" into {output}')
  input_files = glob.glob(input)
  input_str = ','.join([ 'file:' + f for f in input_files])
  if len(input_str) == 0:
    raise RuntimeError("mk_genTuple: input not found.")
  out_dir, _ = os.path.split(output)
  os.makedirs(out_dir, exist_ok=True)
  if os.path.exists(output):
    os.remove(output)
  out_tmp = output + '.tmp.root'
  env = get_cmsenv(cmssw)
  ps_call(['cmsRun', config, f'inputFiles={input_str}', f'output={out_tmp}', f'source={source}'],
          env=env, verbose=verbose)
  shutil.move(out_tmp, output)
  print(f'GenTuple "{output}" successfully created.')

if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Create l1Tuples adding generator level info.')
  parser.add_argument('--input', required=True, type=str, help="input file or glob pattern")
  parser.add_argument('--output', required=True, type=str, help="output file")
  parser.add_argument('--source', required=False, type=str, default="genParticles",
                      help="collection of generated partilces. E.g. genParticles, prunedGenParticles etc.")
  parser.add_argument('--config', required=False, type=str,
                      default=os.path.join(os.environ['ANALYSIS_PATH'], 'MCProd', 'gentuple_cff.py'),
                      help="python file with CMSSW configuration")
  parser.add_argument('--cmssw', required=False, type=str, default=os.environ['DEFAULT_CMSSW_HOME'],
                      help="path to the CMSSW installation")
  parser.add_argument('--verbose', required=False, type=int, default=1, help="verbosity level")
  args = parser.parse_args()

  mk_genTuple(args.input, args.output, args.source, args.config, args.cmssw, args.verbose)
