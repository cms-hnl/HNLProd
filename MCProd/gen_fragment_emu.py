import FWCore.ParameterSet.Config as cms

externalLHEProducer = cms.EDProducer("ExternalLHEProducer",
    args = cms.vstring(''),
    nEvents = cms.untracked.uint32(1),
    numberOfParameters = cms.uint32(1),
    outputFile = cms.string('cmsgrid_final.lhe'),
    scriptName = cms.FileInPath('GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh')
)

from Configuration.Generator.Pythia8CommonSettings_cfi import *
from Configuration.Generator.MCTunes2017.PythiaCP5Settings_cfi import *
from Configuration.Generator.PSweightsPythia.PythiaPSweightsSettings_cfi import *

generator = cms.EDFilter("Pythia8HadronizerFilter",
    maxEventsToPrint = cms.untracked.int32(1),
    pythiaPylistVerbosity = cms.untracked.int32(1),
    filterEfficiency = cms.untracked.double(1.0),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    comEnergy = cms.double(13000.),
    PythiaParameters = cms.PSet(
        pythia8CommonSettingsBlock,
        pythia8CP5SettingsBlock,
        pythia8PSweightsSettingsBlock,
        processParameters = cms.vstring('LesHouches:setLifetime = 2'),
        parameterSets = cms.vstring('pythia8CommonSettings',
                                    'pythia8CP5Settings',
                                    'pythia8PSweightsSettings',
                                    'processParameters',
                                    )
    )
)

leptonFilter = cms.EDFilter("MCMultiParticleFilter",
    NumRequired = cms.int32(2),
    AcceptMore = cms.bool(True),
    ParticleID = cms.vint32(11, 13),
    PtMin = cms.vdouble([0.] * 2),
    EtaMax = cms.vdouble([999.] * 2),
    Status = cms.vint32([1] * 2),
    MinDecayRadius = cms.untracked.vdouble([25.] * 2), # in mm
    MaxDecayRadius = cms.untracked.vdouble([8000.] * 2), # in mm
    MaxDecayZ = cms.untracked.vdouble([12000.] * 2), # in mm
)

ProductionFilterSequence = cms.Sequence(generator * leptonFilter)

