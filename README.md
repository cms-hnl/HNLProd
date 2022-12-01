# HNLProd
Tools to run a private MC production

## How to run MC production

Central HNL LO cards:
https://github.com/cms-sw/genproductions/tree/e3bf0a9b8180b78938a34e4d06036d5dd096d8ef/bin/MadGraph5_aMCatNLO/cards/production/2017/13TeV/exo_heavyNeutrino_LO

Update yaml config with relevant setup (output paths, couplings, masses, number of events etc.) and then run `RunProd` task.
```shell
source env.sh
law run RunProd --setup config/mc_prod_setups/Run2_mu.yaml
```

If you want to run only the generator step:
- set `last_step: LHEGEN` in the config
- after `RunProd` is finished, to create nanoAOD with only `GenPart` content run:
  ```shell
  python MCProd/mk_genTuple.py --input INPUT_FILE --output OUTPUT_FILE
  ```