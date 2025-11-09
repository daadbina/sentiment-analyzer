# Trainer & Model Registry Service - TODO List

**Service**: trainer-model-registry-service  
**Version**: 1.0.5  
**Last Updated**: 2025-11-09  
**Status**: In Development - BTC Price Feature Integration

---

## Current Sprint: BTC Price Feature Integration

### Task 1: Feature Retriever Update ✅ COMPLETE
- [x] Update src/data/feature_retriever.py
  - [x] Add 4 new BTC price features to feature list
  - [x] Update feature names: btc_change_pct_10h, btc_volatility_score, btc_volume, btc_label_spike
  - [x] Update Feast query to include BTC features
  - [x] Add logging for BTC feature retrieval
  - [x] Handle missing BTC features gracefully

### Task 2: Feature Engineering Update
- [ ] Update src/data/feature_engineer.py
  - [ ] Add BTC feature interactions (e.g., sentiment_mean * btc_change_pct_10h)
  - [ ] Add BTC feature ratios (e.g., btc_volatility_score / sentiment_std)
  - [ ] Include BTC features in polynomial transformations
  - [ ] Add logging for BTC feature engineering

### Task 3: Preprocessor Update
- [ ] Update src/data/preprocessor.py
  - [ ] Ensure BTC features are included in scaling
  - [ ] Handle missing BTC features (imputation or default values)
  - [ ] Add logging for BTC feature preprocessing

### Task 4: Model Training Update
- [ ] Update src/training/trainer.py
  - [ ] Verify BTC features are included in training data
  - [ ] Add logging for BTC feature importance
  - [ ] Track BTC feature contribution to model performance

### Task 5: Label Retriever Update ✅ COMPLETE
- [x] Update src/data/label_retriever.py
  - [x] Add BTC price change labels from btc_truth table
  - [x] Implement retrieve_btc_labels() method
  - [x] Add temporal alignment logic for BTC labels
  - [x] Add logging for BTC label retrieval

### Task 6: Model Evaluation Update
- [ ] Update src/evaluation/evaluator.py
  - [ ] Add BTC price prediction metrics (MAE, RMSE, Pearson correlation)
  - [ ] Track BTC prediction accuracy separately
  - [ ] Add logging for BTC prediction performance

### Task 7: Configuration Update
- [ ] Update src/config.py
  - [ ] Add BTC feature configuration
  - [ ] Add BTC label configuration
  - [ ] Add BTC prediction enable/disable flag

### Task 8: Testing
- [ ] Create tests/unit/test_btc_feature_retrieval.py
  - [ ] Test BTC feature retrieval from Feast
  - [ ] Test BTC label retrieval from PostgreSQL
  - [ ] Test BTC feature engineering
  - [ ] Achieve ≥90% coverage

### Task 9: Integration Testing
- [ ] Test end-to-end with BTC features
  - [ ] Verify BTC features are retrieved from Feast
  - [ ] Verify BTC labels are retrieved from PostgreSQL
  - [ ] Verify models are trained with BTC features
  - [ ] Verify BTC prediction metrics are computed

### Task 10: Documentation
- [ ] Update CHANGELOG.md with BTC feature integration
- [ ] Update TODO.md with completion status
- [ ] Add BTC prediction documentation to README.md

---

## Summary

**Total Tasks**: 10
**Completed**: 2 (Tasks 1, 5)
**In Progress**: 1 (Task 2 - Feature Engineering)
**Remaining**: 7

**Current Phase**: BTC Price Feature Integration
**Next Milestone**: Complete feature engineering and model training updates

---

**Last Updated**: 2025-11-09  
**Maintainer**: Trainer & Model Registry Service Team

