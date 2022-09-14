import law
import luigi
import math
import os
import re
import shutil
import tempfile
import yaml
from .mk_prodcard import ProdCard, mk_prodcard
from .mk_gridpack import find_gridpack, mk_gridpack
from .run_prod import run_prod, step_to_file_name
from RunKit.grid_helper_tasks import CreateVomsProxy

law.contrib.load("htcondor")

def parse_int_list(orig_list):
  result = set()
  def parse_str(item):
    match = re.match(r'^[0-9]+$', item)
    if match:
      return [int(item)]
    match = re.match(r'^([0-9]+) *- *([0-9]+)$', item)
    if match:
      start = int(match.group(1))
      end = int(match.group(2))
      if start <= end:
        return list(range(start, end+1))
    raise RuntimeError(f'parse_int_list: unknown range expression "{item}"')

  for item in orig_list:
    if type(item) == int:
      result.add(item)
    elif type(item) == str:
      result.update(parse_str(item))
    else:
      raise RuntimeError(f'parse_int_list: unsupported item type "{type(item)}" for "{item}"')
  return sorted(list(result))

def create_point(prod_setup, cond, point_params):
  params = { 'com_energy': cond['default']['comEnergy'] }
  params.update(point_params)
  if 'default' in prod_setup:
    params.update(prod_setup['default'])
  params['prod_card'] = ProdCard(params['type'], params['mass'], params['e_mixing'], params['mu_mixing'],
                                 params['tau_mixing'], params['com_energy'])
  params['runs'] = parse_int_list(params.get('runs', []))
  return params

class Task(law.Task):
  setup = luigi.Parameter()

  setup_path = None
  prod_setup = None
  cond = None
  points = None

  def __init__(self, *args, **kwargs):
    super(Task, self).__init__(*args, **kwargs)
    setup_path = self.to_abs(self.setup)
    if Task.setup_path is None:
      with open(setup_path, 'r') as f:
        Task.prod_setup = yaml.safe_load(f)
      cond_path = self.to_abs(self.prod_setup['cond_config'])
      with open(cond_path, 'r') as f:
        Task.cond = yaml.safe_load(f)
      Task.points = [ create_point(self.prod_setup, self.cond, p) for p in self.prod_setup['points'] ]
      Task.setup_path = setup_path
    if setup_path != Task.setup_path:
      raise RuntimeError("Inconsistent setup path")
    self.prod_setup = Task.prod_setup
    self.cond = Task.cond
    self.points = Task.points

  def store_parts(self):
    return (self.__class__.__name__, )

  def ana_path(self):
    return os.getenv("ANALYSIS_PATH")

  def ana_data_path(self):
    return os.getenv("ANALYSIS_DATA_PATH")

  def local_path(self, *path):
    parts = (self.ana_data_path(),) + self.store_parts() + path
    return os.path.join(*parts)

  def local_target(self, *path):
    return law.LocalFileTarget(self.local_path(*path))

  def to_abs(self, path):
    if len(path) == 0:
      return self.ana_path()
    if path[0] == '/':
      return path
    return os.path.join(self.ana_path(), path)

class HTCondorWorkflow(law.htcondor.HTCondorWorkflow):
  max_runtime = law.DurationParameter(default=12.0, unit="h", significant=True,
                                      description="maximum runtime, default unit is hours")
  n_cpus = luigi.IntParameter(default=1, description="number of CPU slots")

  def htcondor_output_directory(self):
    # the directory where submission meta data should be stored
    return law.LocalDirectoryTarget(self.local_path())

  def htcondor_bootstrap_file(self):
    # each job can define a bootstrap file that is executed prior to the actual job
    # in order to setup software and environment variables
    return os.path.join(self.ana_path(), 'bootstrap.sh')

  def htcondor_job_config(self, config, job_num, branches):
    config.render_variables["analysis_path"] = self.ana_path()
    config.custom_content.append(("requirements", '(OpSysAndVer =?= "CentOS7")'))
    config.custom_content.append(("+MaxRuntime", int(math.floor(self.max_runtime * 3600)) - 1))
    n_cpus = int(self.n_cpus)
    if n_cpus > 1:
      config.custom_content.append(("RequestCpus", n_cpus))

    log_path = os.path.abspath(os.path.join(self.ana_data_path(), 'logs'))
    os.makedirs(log_path, exist_ok=True)
    config.custom_content.append(("log", os.path.join(log_path, 'job.$(ClusterId).$(ProcId).log')))
    config.custom_content.append(("output", os.path.join(log_path, 'job.$(ClusterId).$(ProcId).out')))
    config.custom_content.append(("error", os.path.join(log_path, 'job.$(ClusterId).$(ProcId).err')))
    return config

class MkProdcard(Task, law.LocalWorkflow):
  def create_branch_map(self):
    branches = {}
    for task_id, point in enumerate(self.points):
      branches[task_id] = point
    return branches

  def output(self):
    point = self.branch_data
    done_flag = os.path.join(self.prod_setup['prodcard_storage'], point['prod_card'].name, '.done')
    return law.LocalFileTarget(done_flag)

  def run(self):
    point = self.branch_data
    templates = self.to_abs(self.prod_setup['prodcard_templates'])
    mk_prodcard(templates, self.prod_setup['prodcard_storage'], point['prod_card'])
    self.output().touch()

class MkGridpack(Task, HTCondorWorkflow, law.LocalWorkflow):
  def __init__(self, *args, **kwargs):
    if 'max_runtime' not in kwargs:
      kwargs['max_runtime'] = 1
    super(MkGridpack, self).__init__(*args, **kwargs)

  def workflow_requires(self):
    return { "prodcard": MkProdcard.req(self, workflow='local') }

  def requires(self):
    return MkProdcard.req(self, workflow='local')

  def create_branch_map(self):
    branches = {}
    for task_id, point in enumerate(self.points):
      branches[task_id] = point
    return branches

  def output(self):
    point = self.branch_data
    done_flag = os.path.join(self.prod_setup['gridpack_storage'], point['prod_card'].name, '.done')
    return law.LocalFileTarget(done_flag)

  def run(self):
    point = self.branch_data
    print(f"Creating gridpack for {point['prod_card'].name}...")
    prodcard_dir = os.path.join(self.prod_setup['prodcard_storage'], point['prod_card'].name)
    mk_gridpack(prodcard_dir, self.prod_setup['gridpack_storage'])
    self.output().touch()

class RunProd(Task, HTCondorWorkflow, law.LocalWorkflow):
  def __init__(self, *args, **kwargs):
    if 'max_runtime' not in kwargs:
      kwargs['max_runtime'] = 24
    if 'n_cpus' not in kwargs:
      kwargs['n_cpus'] = 2
    super(RunProd, self).__init__(*args, **kwargs)

  def workflow_requires(self):
    return { "voms": CreateVomsProxy.req(self), "gridpack": MkGridpack.req(self, n_cpus=1, max_runtime=1) }

  # def requires(self):
  #   point_id, point, era, run = self.branch_data
  #   return [ CreateVomsProxy.req(self), MkGridpack.req(self, n_cpus=1, max_runtime=1, branch=point_id) ]

  def create_branch_map(self):
    branches = {}
    task_id = 0
    for era_id, era in enumerate(self.prod_setup['eras']):
      for point_id, point in enumerate(self.points):
        for run in point['runs']:
          branches[task_id] = (point_id, point, era, run)
          task_id += 1
    return branches

  def output(self):
    point_id, point, era, run = self.branch_data
    file_name_prefix = step_to_file_name[self.prod_setup['last_step']]
    file_name = f'{file_name_prefix}_{run}.root'
    root_file = os.path.join(self.prod_setup['output_storage'], era, point['prod_card'].name, file_name)
    return law.LocalFileTarget(root_file)

  def law_job_home(self):
    if 'LAW_JOB_HOME' in os.environ:
      return os.environ['LAW_JOB_HOME'], False
    return tempfile.mkdtemp(dir=self.local_path()), True

  def run(self):
    point_id, point, era, run = self.branch_data
    print(f"Running production {point['prod_card'].name} era={era} run={run}...")
    gridpack_dir = os.path.join(self.prod_setup['gridpack_storage'], point['prod_card'].name)
    gridpack_file, gridpack_cond = find_gridpack(gridpack_dir, point['prod_card'].name)
    gridpack_path = os.path.join(gridpack_dir, gridpack_file)
    fragment_path = self.to_abs(self.prod_setup['gen_fragment'])
    cond_path = self.to_abs(self.prod_setup['cond_config'])
    last_step = self.prod_setup['last_step']
    n_evt = point['events_per_run']
    output_dir, output_file = os.path.split(self.output().path)
    work_dir, work_dir_is_tmp = self.law_job_home()
    run_prod(gridpack_path, fragment_path, cond_path, era, last_step, run, n_evt, output_dir, work_dir,
             remove_outputs=True)
    if work_dir_is_tmp:
      shutil.rmtree(work_dir)
