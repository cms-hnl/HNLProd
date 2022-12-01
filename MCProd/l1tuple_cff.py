# Auto generated configuration file (with modification)
# using:
# Revision: 1.19
# Source: /local/reps/CMSSW/CMSSW/Configuration/Applications/python/ConfigBuilder.py,v
# with command line options: cmsDriver.py l1Ntuple -s RAW2DIGI --python_filename=mc.py -n -1 --no_output --era=Run3 --mc --conditions=124X_mcRun3_2022_realistic_v10 --customise=L1Trigger/Configuration/customiseReEmul.L1TReEmulMCFromRAWSimHcalTP --customise=L1Trigger/L1TNtuples/customiseL1Ntuple.L1NtupleRAWEMU --customise=L1Trigger/Configuration/customiseSettings.L1TSettingsToCaloParams_2022_v0_4 --filein=/store/mc/Run3Winter22DR/SingleNeutrino_E-10-gun/GEN-SIM-DIGI-RAW/L1TPU0to99FEVT_SNB_122X_mcRun3_2021_realistic_v9-v2/2520004/23eb7d6b-ffbd-4368-9d99-92c5f153f570.root
import FWCore.ParameterSet.Config as cms

from Configuration.Eras.Era_Run3_cff import Run3
import FWCore.ParameterSet.VarParsing as VarParsing

process = cms.Process('RAW2DIGI', Run3)

options = VarParsing.VarParsing ('analysis')
options.register('outL1', 'l1.root', VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string,
                 'Output file with L1 ntuple')
options.register('outGen', 'gen.root', VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string,
                 'Output file with gen particles')
options.parseArguments()

process.maxEvents = cms.untracked.PSet(
  input = cms.untracked.int32(options.maxEvents)
)

# import of standard configurations
process.load('Configuration.StandardSequences.Services_cff')
process.load('SimGeneral.HepPDTESSource.pythiapdt_cfi')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.load('Configuration.EventContent.EventContent_cff')
process.load('SimGeneral.MixingModule.mixNoPU_cfi')
process.load('Configuration.StandardSequences.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_cff')
process.load('Configuration.StandardSequences.RawToDigi_cff')
process.load('Configuration.StandardSequences.EndOfProcess_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_cff')

process.MessageLogger.suppressWarning = cms.untracked.vstring(
    'l1PhaseIITree', 'l1UpgradeTfMuonEmuTree', 'l1CaloTowerTree',
    'l1UpgradeTfMuonTree','l1UpgradeTree','l1HOTree', 'l1Phase2CaloTree')

# Input source
process.source = cms.Source("PoolSource",
  fileNames = cms.untracked.vstring(options.inputFiles),
)

# end ADDED

process.options = cms.untracked.PSet(
    FailPath = cms.untracked.vstring(),
    IgnoreCompletely = cms.untracked.vstring(),
    Rethrow = cms.untracked.vstring(),
    SkipEvent = cms.untracked.vstring(),
    allowUnscheduled = cms.obsolete.untracked.bool,
    canDeleteEarly = cms.untracked.vstring(),
    emptyRunLumiMode = cms.obsolete.untracked.string,
    eventSetup = cms.untracked.PSet(
        forceNumberOfConcurrentIOVs = cms.untracked.PSet(
            allowAnyLabel_=cms.required.untracked.uint32
        ),
        numberOfConcurrentIOVs = cms.untracked.uint32(1)
    ),
    fileMode = cms.untracked.string('FULLMERGE'),
    forceEventSetupCacheClearOnNewRun = cms.untracked.bool(False),
    makeTriggerResults = cms.obsolete.untracked.bool,
    numberOfConcurrentLuminosityBlocks = cms.untracked.uint32(1),
    numberOfConcurrentRuns = cms.untracked.uint32(1),
    numberOfStreams = cms.untracked.uint32(0),
    numberOfThreads = cms.untracked.uint32(1),
    printDependencies = cms.untracked.bool(False),
    sizeOfStackForThreadsInKB = cms.optional.untracked.uint32,
    throwIfIllegalParameter = cms.untracked.bool(True),
    wantSummary = cms.untracked.bool(False)
)

# Production Info
process.configurationMetadata = cms.untracked.PSet(
    annotation = cms.untracked.string('l1Ntuple nevts:-1'),
    name = cms.untracked.string('Applications'),
    version = cms.untracked.string('$Revision: 1.19 $')
)

# Output definition
process.NANOAODSIMoutput = cms.OutputModule("NanoAODOutputModule",
    compressionAlgorithm = cms.untracked.string('LZMA'),
    compressionLevel = cms.untracked.int32(9),
    dataset = cms.untracked.PSet(
        dataTier = cms.untracked.string('NANOAODSIM'),
        filterName = cms.untracked.string('')
    ),
    fileName = cms.untracked.string('file:' + options.outGen),
    outputCommands = process.NANOAODSIMEventContent.outputCommands
)
process.load('PhysicsTools.NanoAOD.nano_cff')
from PhysicsTools.NanoAOD.nano_cff import nanoAOD_customizeMC

#call to customisation function nanoAOD_customizeMC imported from PhysicsTools.NanoAOD.nano_cff
process = nanoAOD_customizeMC(process)

process.nanoAOD_step = cms.Path(process.nanoSequenceMC)
process.NANOAODSIMoutput_step = cms.EndPath(process.NANOAODSIMoutput)

process.nanoTableTaskFS = cms.Task(process.genParticleTablesTask, process.genParticleTask)
process.nanoSequenceFS = cms.Sequence(process.nanoTableTaskFS)
process.nanoSequenceMC = cms.Sequence(process.nanoTableTaskFS)
process.finalGenParticles.src = cms.InputTag("genParticles")
process.NANOAODSIMoutput.outputCommands = cms.untracked.vstring(
  'drop *',
  'keep nanoaodFlatTable_*Table_*_*',
)

process.MessageLogger.cerr.FwkReport.reportEvery = 100

def customiseGenParticles(process):
  def pdgOR(pdgs):
    abs_pdgs = [ f'abs(pdgId) == {pdg}' for pdg in pdgs ]
    return '( ' + ' || '.join(abs_pdgs) + ' )'

  leptons = pdgOR([ 11, 13, 15 ])
  important_particles = pdgOR([ 6, 23, 24, 25, 35, 39, 9990012, 9900012 ])
  process.finalGenParticles.select = [
    'drop *',
    'keep++ statusFlags().isLastCopy() && ' + leptons,
    '+keep statusFlags().isFirstCopy() && ' + leptons,
    'keep+ statusFlags().isLastCopy() && ' + important_particles,
    '+keep statusFlags().isFirstCopy() && ' + important_particles,
    "drop abs(pdgId) == 2212 && abs(pz) > 1000", #drop LHC protons accidentally added by previous keeps
  ]

  from PhysicsTools.NanoAOD.common_cff import Var
  for coord in [ 'x', 'y', 'z' ]:
    setattr(process.genParticleTable.variables, 'v' + coord,
            Var(f'vertex().{coord}', float, precision=10,
                doc=f'{coord} coordinate of the gen particle production vertex'))
  process.genParticleTable.variables.mass.expr = cms.string('mass')
  process.genParticleTable.variables.mass.doc = cms.string('mass')

  return process

process = customiseGenParticles(process)

# Additional output definition

# Other statements
from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, '124X_mcRun3_2022_realistic_v10', '')

# Path and EndPath definitions
process.raw2digi_step = cms.Path(process.RawToDigi)
process.endjob_step = cms.EndPath(process.endOfProcess)

# Schedule definition
process.schedule = cms.Schedule(process.raw2digi_step, process.nanoAOD_step, process.endjob_step, process.NANOAODSIMoutput_step)
from PhysicsTools.PatAlgos.tools.helpers import associatePatAlgosToolsTask
associatePatAlgosToolsTask(process)

# customisation of the process.

# Automatic addition of the customisation function from L1Trigger.Configuration.customiseReEmul
from L1Trigger.Configuration.customiseReEmul import L1TReEmulMCFromRAWSimHcalTP

#call to customisation function L1TReEmulMCFromRAWSimHcalTP imported from L1Trigger.Configuration.customiseReEmul
process = L1TReEmulMCFromRAWSimHcalTP(process)

# Automatic addition of the customisation function from L1Trigger.L1TNtuples.customiseL1Ntuple
from L1Trigger.L1TNtuples.customiseL1Ntuple import L1NtupleRAWEMU

#call to customisation function L1NtupleRAWEMU imported from L1Trigger.L1TNtuples.customiseL1Ntuple
process = L1NtupleRAWEMU(process)

# Automatic addition of the customisation function from L1Trigger.Configuration.customiseSettings
from L1Trigger.Configuration.customiseSettings import L1TSettingsToCaloParams_2022_v0_4

#call to customisation function L1TSettingsToCaloParams_2022_v0_2 imported from L1Trigger.Configuration.customiseSettings
process = L1TSettingsToCaloParams_2022_v0_4(process)

# End of customisation functions

# Customisation from command line
process.TFileService.fileName = cms.string(options.outL1)

# Add early deletion of temporary data products to reduce peak memory need
from Configuration.StandardSequences.earlyDeleteSettings_cff import customiseEarlyDelete
process = customiseEarlyDelete(process)
# End adding early deletion

#print(process.dumpPython())