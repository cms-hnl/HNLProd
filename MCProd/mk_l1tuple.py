import os
import re
import shutil
from RunKit.run_tools import ps_call

def mk_l1tuple(file_in, file_out, work_dir, config, env=None, verbose=1):
  if verbose > 0:
    print(f'Processing "{file_in}" into {file_out}')
  out_dir, out_filename = os.path.split(file_out)
  os.makedirs(out_dir, exist_ok=True)
  tuple_only = os.path.join(work_dir, out_filename + '.A.root')
  gen_only = os.path.join(work_dir, out_filename + '.B.root')
  out_tmp = os.path.join(work_dir, out_filename + '.hadd.root')
  ps_call(['cmsRun', config, f'inputFiles=file:{file_in}', f'outL1={tuple_only}',
           f'outGen={gen_only}'], cwd=work_dir, env=env, verbose=verbose)
  ps_call(['hadd', '-ff', out_tmp, tuple_only, gen_only], verbose=1)
  shutil.move(out_tmp, file_out)
  os.remove(tuple_only)
  os.remove(gen_only)
  print(f'L1 tuple "{file_out}" created.')

# def mk_l1tuples(input_dir, output_dir, input_name_pattern, output_name_prefix):
#   print(output_dir)
#   for dirpath, dirnames, filenames in os.walk(input_dir):
#     dirpath = os.path.relpath(dirpath, input_dir)
#     for file in filenames:
#       match = re.match(input_name_pattern, file)
#       if match is not None:
#         file_in_path = os.path.join(input_dir, dirpath, file)
#         job_id = match.group(1)
#         file_out_path = os.path.join(output_dir, dirpath, f'{output_name_prefix}_{job_id}.root')
#         if not os.path.exists(file_out_path):
#           mk_l1tuple(file_in_path, file_out_path)


if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Create l1Tuples adding generator level info.')
  parser.add_argument('--input', required=True, type=str, help="input file")
  parser.add_argument('--output', required=True, type=str, help="output file")
  parser.add_argument('--workdir', required=True, type=str, help="work directory")
  parser.add_argument('--config', required=True, type=str, help="python file with CMSSW configuration")
  parser.add_argument('--verbose', required=False, type=int, default=1, help="verbosity level")
  args = parser.parse_args()

  mk_l1tuple(args.input, args.output, args.workdir, args.config, args.verbose)
