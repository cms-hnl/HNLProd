import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing

options = VarParsing.VarParsing ('analysis')
options.register('output', 'gen.root', VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string,
                 'Output file with gen particles')
options.parseArguments()

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

process = cms.Process('NANO')
process.load('Configuration.StandardSequences.Services_cff')
process.load('Configuration.EventContent.EventContent_cff')
process.load('Configuration.StandardSequences.EndOfProcess_cff')
process.load('PhysicsTools.NanoAOD.nano_cff')

process.source = cms.Source("PoolSource",
  fileNames = cms.untracked.vstring(options.inputFiles),
)

process.NANOAODSIMoutput = cms.OutputModule("NanoAODOutputModule",
    compressionAlgorithm = cms.untracked.string('LZMA'),
    compressionLevel = cms.untracked.int32(9),
    dataset = cms.untracked.PSet(
        dataTier = cms.untracked.string('NANOAODSIM'),
        filterName = cms.untracked.string('')
    ),
    fileName = cms.untracked.string('file:' + options.output),
    outputCommands = process.NANOAODSIMEventContent.outputCommands
)

from PhysicsTools.NanoAOD.nano_cff import nanoAOD_customizeMC
process = nanoAOD_customizeMC(process)

process.nanoAOD_step = cms.Path(process.nanoSequenceMC)
process.NANOAODSIMoutput_step = cms.EndPath(process.NANOAODSIMoutput)
process.endjob_step = cms.EndPath(process.endOfProcess)

process.nanoTableTaskFS = cms.Task(process.genParticleTablesTask, process.genParticleTask)
process.nanoSequenceFS = cms.Sequence(process.nanoTableTaskFS)
process.nanoSequenceMC = cms.Sequence(process.nanoTableTaskFS)
process.finalGenParticles.src = cms.InputTag("genParticles")
process.NANOAODSIMoutput.outputCommands = cms.untracked.vstring(
  'drop *',
  'keep nanoaodFlatTable_*Table_*_*',
)

process = customiseGenParticles(process)
process.schedule = cms.Schedule(process.nanoAOD_step, process.endjob_step, process.NANOAODSIMoutput_step)
process.MessageLogger.cerr.FwkReport.reportEvery = 100
